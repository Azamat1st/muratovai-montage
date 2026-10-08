// Person segmentation with Apple Vision (VNGeneratePersonSegmentationRequest, .accurate): video → grayscale mask video (same size/fps).
// Build: swiftc -O -target arm64-apple-macos12.0 person_mask.swift -o person_mask   (Apple Vision person segmentation needs macOS 12+)
// Usage: person_mask <in.mp4> <out_mask.mp4> [--frame <sec> <out.png>]
// Then: ffmpeg -i in.mp4 -i out_mask.mp4 -filter_complex "[1:v]format=gray[m];[0:v][m]alphamerge,format=yuva420p" -c:v libvpx-vp9 -b:v 0 -crf 18 -pix_fmt yuva420p subject.webm
import AVFoundation
import Vision
import CoreImage
import Foundation

let args = CommandLine.arguments
guard args.count > 2 else { fputs("usage: person_mask <in.mp4> <out_mask.mp4> [--frame <sec> <out.png>]\n", stderr); exit(1) }
let inURL = URL(fileURLWithPath: args[1])
let ctx = CIContext()
let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8

func mask(for pb: CVPixelBuffer) -> CIImage? {
    let h = VNImageRequestHandler(cvPixelBuffer: pb, options: [:])
    try? h.perform([req])
    guard let m = req.results?.first?.pixelBuffer else { return nil }
    let W = CGFloat(CVPixelBufferGetWidth(pb)), H = CGFloat(CVPixelBufferGetHeight(pb))
    let mi = CIImage(cvPixelBuffer: m)
    return mi.transformed(by: CGAffineTransform(scaleX: W / mi.extent.width, y: H / mi.extent.height))
}

let asset = AVURLAsset(url: inURL)
if args.count > 3 && args[3] == "--frame" {
    let gen = AVAssetImageGenerator(asset: asset); gen.appliesPreferredTrackTransform = true
    let t = CMTime(seconds: Double(args[4])!, preferredTimescale: 600)
    let cg = try! gen.copyCGImage(at: t, actualTime: nil)
    let h = VNImageRequestHandler(cgImage: cg, options: [:]); try! h.perform([req])
    let m = CIImage(cvPixelBuffer: req.results!.first!.pixelBuffer)
    let s = m.transformed(by: CGAffineTransform(scaleX: CGFloat(cg.width) / m.extent.width, y: CGFloat(cg.height) / m.extent.height))
    let out = ctx.createCGImage(s, from: s.extent)!
    let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: args[5]) as CFURL, "public.png" as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, out, nil); CGImageDestinationFinalize(dest); exit(0)
}
let reader = try! AVAssetReader(asset: asset)
let track = asset.tracks(withMediaType: .video)[0]
let out = AVAssetReaderTrackOutput(track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
reader.add(out); reader.startReading()
let size = track.naturalSize
let writer = try! AVAssetWriter(outputURL: URL(fileURLWithPath: args[2]), fileType: .mp4)
let wi = AVAssetWriterInput(mediaType: .video, outputSettings: [AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: Int(size.width), AVVideoHeightKey: Int(size.height),
    AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 12_000_000]])
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: wi, sourcePixelBufferAttributes: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: Int(size.width), kCVPixelBufferHeightKey as String: Int(size.height)])
writer.add(wi); writer.startWriting(); writer.startSession(atSourceTime: .zero)
var n = 0
while let sb = out.copyNextSampleBuffer() {
    guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
    let pts = CMSampleBufferGetPresentationTimeStamp(sb)
    guard let m = mask(for: pb) else { continue }
    var outPB: CVPixelBuffer?
    CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &outPB)
    ctx.render(m.applyingFilter("CIColorMatrix", parameters: [:]), to: outPB!)
    while !wi.isReadyForMoreMediaData { usleep(2000) }
    adaptor.append(outPB!, withPresentationTime: pts); n += 1
    if n % 300 == 0 { fputs("mask frame \(n)\n", stderr) }
}
wi.markAsFinished(); let sem = DispatchSemaphore(value: 0); writer.finishWriting { sem.signal() }; sem.wait()
print("frames \(n)")
