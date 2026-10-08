// Face track for framing: samples a video at N fps, runs Apple Vision face landmarks, prints JSON
// [{t, x, y, w, h, eye_y, cx}] in pixel coordinates of the source (origin top-left).
// Build: swiftc -O -target arm64-apple-macos12.0 face_track.swift -o face_track
// Usage: face_track <video> [fps=2] > face.json
import AVFoundation
import Vision
import Foundation

let args = CommandLine.arguments
guard args.count > 1 else { fputs("usage: face_track <video> [fps]\n", stderr); exit(1) }
let url = URL(fileURLWithPath: args[1])
let fps = args.count > 2 ? Double(args[2]) ?? 2.0 : 2.0
let asset = AVURLAsset(url: url)
let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.requestedTimeToleranceBefore = CMTime(value: 1, timescale: 60)
gen.requestedTimeToleranceAfter = CMTime(value: 1, timescale: 60)
let dur = CMTimeGetSeconds(asset.duration)
var out: [[String: Double]] = []
var t = 0.0
while t < dur {
    let time = CMTime(seconds: t, preferredTimescale: 600)
    if let cg = try? gen.copyCGImage(at: time, actualTime: nil) {
        let W = Double(cg.width), H = Double(cg.height)
        let req = VNDetectFaceLandmarksRequest()
        let handler = VNImageRequestHandler(cgImage: cg, options: [:])
        try? handler.perform([req])
        if let faces = req.results, let f = faces.max(by: { $0.boundingBox.width < $1.boundingBox.width }) {
            let bb = f.boundingBox  // normalized, origin bottom-left
            let x = bb.minX * W, w = bb.width * W, h = bb.height * H
            let y = (1.0 - bb.maxY) * H
            var eyeY = y + h * 0.42
            if let le = f.landmarks?.leftEye, let re = f.landmarks?.rightEye {
                let pts = le.normalizedPoints + re.normalizedPoints
                let my = pts.map { Double($0.y) }.reduce(0, +) / Double(pts.count)  // relative to bbox, origin bottom-left
                eyeY = (1.0 - (bb.minY + my * bb.height)) * H
            }
            out.append(["t": t, "x": x, "y": y, "w": w, "h": h, "eye_y": eyeY, "cx": x + w / 2, "W": W, "H": H])
        } else {
            out.append(["t": t, "W": W, "H": H])
        }
    }
    t += 1.0 / fps
}
let data = try! JSONSerialization.data(withJSONObject: out, options: [])
print(String(data: data, encoding: .utf8)!)
