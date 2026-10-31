# macOS Windows Keyboard

กฎ Karabiner-Elements สำหรับใช้คีย์บอร์ดภายนอกบน macOS: กด Backtick เพื่อสลับไทย–อังกฤษ และใช้ปุ่ม Ctrl แบบ Windows

## ปุ่มที่รองรับ

| ปุ่มบนคีย์บอร์ดภายนอก | ส่งให้ macOS | การทำงาน |
| --- | --- | --- |
| Backtick เดี่ยว | Control + Space | สลับแหล่งป้อนเข้า |
| Ctrl + C | Command + C | คัดลอก |
| Ctrl + V | Command + V | วาง |
| Ctrl + X | Command + X | ตัด |
| Ctrl + Z | Command + Z | ย้อนกลับ |
| Ctrl + A | Command + A | เลือกทั้งหมด |
| Ctrl + S | Command + S | บันทึก |
| Ctrl + F | Command + F | ค้นหา |
| Ctrl + Y | Command + Shift + Z | ทำซ้ำ (Redo) |

- ใช้ได้กับ Ctrl ซ้ายและขวา
- กฎจำกัดเฉพาะคีย์บอร์ดภายนอกด้วย `is_built_in_keyboard: false` ไม่ผูกยี่ห้อหรือรุ่น
- กฎ Ctrl เว้น Apple Terminal และ iTerm2 ส่วนกฎเปลี่ยนภาษายังทำงานในแอปเหล่านี้
- Shift + Backtick ผ่านตามผังภาษาเดิม: ใน ABC จะได้ `~` ส่วนภาษาไทยอาจเป็นอักขระอื่น
- Ctrl + Shift และชุดปุ่มที่ไม่ได้ระบุไว้ไม่ได้เพิ่มการแปลง

## ไฟล์

`karabiner/external-windows-shortcuts.json` เป็นกฎที่นำเข้าได้ ไม่มีโปรไฟล์ทั้งเครื่อง รหัสอุปกรณ์ ไฟล์สำรอง หรือข้อมูลบัญชีส่วนตัว

## ติดตั้ง

1. ติดตั้ง [Karabiner-Elements จากเว็บไซต์ทางการ](https://karabiner-elements.pqrs.org/) และอนุญาตบริการ/สิทธิ์ที่โปรแกรมระบุ ไม่ต้องปิด SIP หรือแก้ไฟล์ระบบ
2. เปิดใช้ภาษา **ABC** และ **Thai** ใน macOS ตรวจว่า **Control + Space** เป็นปุ่มเลือกแหล่งป้อนเข้าก่อนหน้า กฎนี้เพียงส่งปุ่มลัดดังกล่าว ไม่เปลี่ยนค่าปุ่มลัดระบบให้
3. สำรอง `~/.config/karabiner/karabiner.json` ไปยังที่ปลอดภัยก่อนแก้ไข และสำรองไฟล์กฎชื่อเดียวกันหากมีอยู่แล้ว
4. ดาวน์โหลดหรือ clone repo นี้ แล้วคัดลอก `karabiner/external-windows-shortcuts.json` ไปยัง `~/.config/karabiner/assets/complex_modifications/` สร้างโฟลเดอร์หากยังไม่มี **อย่านำไฟล์กฎนี้ไปทับ karabiner.json**
5. เปิด Karabiner → **Devices** ปิด **Modify events** ของคีย์บอร์ดในตัว และเปิดเฉพาะคีย์บอร์ดภายนอกที่ต้องการ เมาส์/แทร็คแพดไม่จำเป็นต้องเปิด
6. ไปที่ **Complex Modifications → Add predefined rule** เลือกกฎจากชุด **External Windows keyboard shortcuts** แล้วเพิ่มกฎที่ต้องการ หากมีรุ่นเก่าของกฎเดียวกัน ให้ปิดกฎเก่าก่อนเพื่อไม่ให้ซ้ำ

คีย์บอร์ดภายนอกมาตรฐานที่ Karabiner รับเหตุการณ์อยู่แล้วจะตรงกับกฎโดยอัตโนมัติ ทั้ง USB และ Bluetooth รุ่นที่รายงานตัวเป็นทั้งคีย์บอร์ดและอุปกรณ์ชี้ตำแหน่งอาจต้องเปิด Modify events ให้ครั้งแรก

## ข้อจำกัด

- ปุ่มใต้ Esc ต้องส่ง `grave_accent_and_tilde` รุ่น ISO/JIS หรือเฟิร์มแวร์บางแบบอาจส่งรหัสต่างกัน ตรวจได้ด้วย EventViewer
- Backtick เดี่ยวบนคีย์บอร์ดภายนอกจะใช้พิมพ์เครื่องหมายเดิมไม่ได้เมื่อเปิดกฎเปลี่ยนภาษา กดค้างจะไม่สลับภาษาซ้ำ
- ถ้ามีแหล่งป้อนเข้ามากกว่าสองภาษา Control + Space อาจสลับไปภาษาอื่นตามประวัติ ไม่รับประกันว่าจะสลับเฉพาะไทย–อังกฤษ
- ข้อยกเว้น Terminal ใช้ bundle ID ของ Apple Terminal และ iTerm2 เท่านั้น ไม่ครอบคลุม Terminal ที่ฝังในแอป เช่น VS Code หรือแอป Terminal อื่น
- Redo ใช้ Command + Shift + Z แอปที่ใช้ปุ่มลัดต่างออกไปต้องเพิ่มกฎเฉพาะแอป
- ปุ่ม Ctrl ที่มีหน้าที่เฉพาะในแอปอื่นอาจถูกแทนด้วยปุ่ม Command ตามตาราง
- Karabiner ต้องทำงานอยู่ การเลือกชนิดคีย์บอร์ดเสมือนและการตั้งค่า Function Keys ของ Karabiner อาจมีผลกับปุ่มอื่น ควรตรวจตามคีย์บอร์ดที่ใช้

## ตรวจสอบ

ไฟล์กฎผ่านตัวตรวจรูปแบบของ Karabiner-Elements 16.3.0 และตรวจว่ากฎโหลดเปิดใช้งานได้ การตรวจดังกล่าวไม่ได้รับรองผลกับทุกคีย์บอร์ด ทุกแอป หรือหลังรีสตาร์ต

คำสั่งตรวจรูปแบบบนเครื่องที่ติดตั้ง Karabiner:

```sh
"/Library/Application Support/org.pqrs/Karabiner-Elements/bin/karabiner_cli" \
  --lint-complex-modifications karabiner/external-windows-shortcuts.json
```

ควรลองกับเอกสารว่าง: สลับภาษาไปมา, Shift + Backtick ใน ABC, Ctrl+C/V/X/Z/A/S/F/Y และตรวจปุ่มคีย์บอร์ดในตัว รวมถึง Ctrl+C ใน Terminal

## ย้อนกลับ

- หยุดกฎใดกฎหนึ่ง: Karabiner → **Complex Modifications** → ปิดสวิตช์กฎนั้น กฎอื่นยังคงทำงาน
- คืนโปรไฟล์ทั้งหมด: สำรองค่าปัจจุบัน แล้วนำ `karabiner.json` ที่สำรองก่อนติดตั้งกลับ ขณะไม่ได้แก้ค่าผ่านหน้าต่าง Settings พร้อมกัน
- ถอนโปรแกรมทั้งหมด: ใช้เมนู **Uninstall** ของ Karabiner เพื่อถอดบริการและไดรเวอร์อย่างถูกต้อง แล้วตรวจสิทธิ์ Accessibility/Input Monitoring และ Login Items & Extensions ที่เพิ่มไว้

## อ้างอิง

- [เงื่อนไขอุปกรณ์](https://karabiner-elements.pqrs.org/docs/json/complex-modifications-manipulator-definition/conditions/device/)
- [ยกเว้นแอป](https://karabiner-elements.pqrs.org/docs/json/complex-modifications-manipulator-definition/conditions/frontmost-application/)
- [เพิ่มกฎของตนเอง](https://karabiner-elements.pqrs.org/docs/manual/configuration/add-your-own-complex-modifications/)
