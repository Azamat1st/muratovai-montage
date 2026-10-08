# muratovai-montage — монтаж рилсов для Claude Code

> Claude: инструкция для тебя — в `START_HERE.md`.

## По-русски

Пакет учит ваш Claude Code монтировать вертикальные видео с говорящей головой: вырезать паузы и дубли, ставить графику ровно
на слова, логотипы компаний, скриншоты сайтов, подписи, музыку и звуки.

Своего стиля у пакета нет. Вы называете блогера, чей монтаж нравится, — Claude разбирает его ролики и сохраняет стиль
отдельным скиллом. Дальше ваши видео монтируются так же.

### Что нужно

- Mac (лучше всего на Apple Silicon) или компьютер с Windows 10/11.
- Claude Code с подпиской Pro или Max. Для монтажа выбирайте самую сильную модель: `/model` → Opus.
- Ключ **ElevenLabs** (обязательно) — распознаёт речь в ваших видео и в роликах блогера:
  https://elevenlabs.io/app/developers/api-keys. Распознавание тратит немного кредитов ElevenLabs за каждую минуту звука.
- Ключ **Apify** (желательно) — скачивает ролики блогера по нику: https://console.apify.com/settings/integrations →
  Personal API token. Около 1 цента за ролик; у Apify есть бесплатный стартовый лимит. Без ключа давайте ссылки на ролики
  или сами файлы.
- Около 3 ГБ на диске и до 15 минут на первую установку.

Ключи вы вставляете сами в файл, который откроет Claude. В чат ключи не отправляйте.

### Как запустить

Откройте Claude Code и пишите по очереди:

1. **«Установи скилл https://github.com/Azamat1st/muratovai-montage»**. Claude скачает пакет, поставит всё нужное, попросит ключи и сделает тестовый ролик
   на 5 секунд.
2. **«Разбери монтаж @ник»** — ник в Instagram блогера, чей монтаж нравится. Claude скачает его последние ролики, посчитает
   склейки, темп, подписи, шрифты, цвета, графику и звуки и соберёт ваш скилл стиля.
3. **«Смонтируй в стиле @ник»** и перетащите своё видео. Claude спросит, чего не хватает: о чём ролик, какие компании и сайты
   в нём звучат, какой призыв в конце, какой цвет. Готовый ролик и лёгкая версия для отправки появятся в папке `~/reels`.
4. **«Обнови скилл»** — когда выйдет новая версия: Claude скачает её по той же ссылке. Ключи и ваши стили сохранятся.

### Если что-то пошло не так

- **Instagram не отдаёт ролики.** Вставьте ключ Apify. Или зайдите в Instagram в браузере (на Mac — Chrome, на Windows —
  Firefox) и разрешите Claude взять оттуда cookies. Или скачайте ролики сами и перетащите файлы.
- **Рендер падает, Chrome закрывается сразу.** Claude Code работает в песочнице. Попросите запустить рендер без неё или
  запустите команду в обычном терминале.
- **На Windows Claude пишет «установлено, но окно его не видит».** Закройте и снова откройте Claude Code.
- **Голова в кадре стоит криво.** Снимайте крупнее: лицо — примерно 40 % ширины кадра. На Windows лицо находится чуть менее
  точно, чем на Mac: проверяйте кадр.
- Логотипы и скриншоты — чужие товарные знаки и сайты: используйте их так, как в обзорных роликах.

## Oʻzbekcha

Paket Claude Code’ni gapiruvchi odam tushirilgan vertikal videolarni montaj qilishga oʻrgatadi: pauza va takrorlarni
qirqadi, grafikani aynan soʻzlarga qoʻyadi, kompaniya logotiplari, sayt skrinshotlari, subtitrlar, musiqa va tovushlar
qoʻshadi.

Paketning oʻz uslubi yoʻq. Siz montaji yoqqan blogerni aytasiz — Claude uning roliklarini tahlil qilib, uslubni alohida
skill sifatida saqlaydi. Keyin videolaringiz xuddi shunday montaj qilinadi.

### Nima kerak

- Mac (eng yaxshisi Apple Silicon) yoki Windows 10/11 kompyuter.
- Pro yoki Max obunali Claude Code. Montaj uchun eng kuchli modelni tanlang: `/model` → Opus.
- **ElevenLabs** kaliti (majburiy) — videolaringizdagi va bloger roliklaridagi nutqni taniydi:
  https://elevenlabs.io/app/developers/api-keys. Har bir daqiqa ovoz uchun ozgina ElevenLabs krediti sarflanadi.
- **Apify** kaliti (tavsiya etiladi) — bloger roliklarini nik boʻyicha yuklab oladi:
  https://console.apify.com/settings/integrations → Personal API token. Har bir rolik taxminan 1 sent; Apify’da bepul
  boshlangʻich limit bor. Kalitsiz roliklarga havolalar yoki fayllarning oʻzini bering.
- Diskda taxminan 3 GB joy va birinchi oʻrnatish uchun 15 daqiqagacha vaqt.

Kalitlarni Claude ochib beradigan faylga oʻzingiz qoʻyasiz. Kalitlarni chatga yubormang.

### Qanday ishga tushirish

Claude Code’ni oching va navbat bilan yozing:

1. **«https://github.com/Azamat1st/muratovai-montage skillini oʻrnat»**. Claude paketni yuklab oladi, kerakli hamma narsani oʻrnatadi, kalitlarni
   soʻraydi va 5 soniyalik test rolik tayyorlaydi.
2. **«@nik montajini tahlil qil»** — montaji yoqqan blogerning Instagram’dagi niki. Claude uning soʻnggi roliklarini
   yuklab, kesimlar, temp, subtitrlar, shriftlar, ranglar, grafika va tovushlarni hisoblaydi va uslub skillingizni yigʻadi.
3. **«@nik uslubida montaj qil»** va videongizni sudrab tashlang. Claude yetishmayotgan narsani soʻraydi: rolik nima haqida,
   qaysi kompaniya va saytlar tilga olinadi, oxirida qanday chaqiruv, qaysi rang. Tayyor rolik va yuborish uchun yengil
   versiyasi `~/reels` papkasida paydo boʻladi.
4. **«Skillni yangila»** — yangi versiya chiqqanda: Claude uni oʻsha havola orqali yuklab oladi. Kalitlar va
   uslublaringiz saqlanib qoladi.

### Muammo boʻlsa

- **Instagram roliklarni bermayapti.** Apify kalitini qoʻying. Yoki brauzerda Instagram’ga kiring (Mac’da — Chrome,
  Windows’da — Firefox) va Claude’ga cookie’larni olishga ruxsat bering. Yoki roliklarni oʻzingiz yuklab, fayllarni sudrab
  tashlang.
- **Render toʻxtab qoladi, Chrome darhol yopiladi.** Claude Code “sandbox”da ishlaydi. Renderni sandbox’siz ishga
  tushirishni soʻrang yoki buyruqni oddiy terminalda ishga tushiring.
- **Windows’da Claude “oʻrnatilgan, lekin oyna uni koʻrmayapti” deydi.** Claude Code’ni yopib, qayta oching.
- **Kadrda bosh qiyshiq turibdi.** Yaqinroqdan suratga oling: yuz kadr kengligining taxminan 40 % ini egallasin.
  Windows’da yuz Mac’dagidan biroz kamroq aniq topiladi: kadrni tekshiring.
- Logotip va skrinshotlar — boshqalarning tovar belgilari va saytlari: ularni sharh roliklaridagidek ishlating.

Litsenziya: MIT (`LICENSE`).
