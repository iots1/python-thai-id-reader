import time
import re
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import toBytes
from smartcard.Exceptions import CardConnectionException

# --- ชุดคำสั่ง APDU พื้นฐาน ---
SELECT_APPLET = [0x00, 0xA4, 0x04, 0x00, 0x08, 0xA0, 0x00, 0x00, 0x00, 0x54, 0x48, 0x00, 0x01]
CMD_CID       = [0x80, 0xB0, 0x00, 0x04, 0x02, 0x00, 0x0D]
CMD_NAME_TH   = [0x80, 0xB0, 0x00, 0x11, 0x02, 0x00, 0x64]
CMD_NAME_EN   = [0x80, 0xB0, 0x00, 0x75, 0x02, 0x00, 0x64]
CMD_ADDRESS   = [0x80, 0xB0, 0x15, 0x79, 0x02, 0x00, 0x64]
CMD_GENDER    = [0x80, 0xB0, 0x00, 0xE1, 0x02, 0x00, 0x01]

class ThaiIDCardObserver(CardObserver):
    def thai_decode(self, data):
        """ฟังก์ชันถอดรหัสภาษาไทยที่เสถียรที่สุด"""
        try:
            return bytes(data).decode('tis-620').strip().replace('#', ' ')
        except Exception:
            return ""

    def send_apdu(self, connection, apdu):
        """ส่งคำสั่งพร้อมหน่วงเวลาเพิ่มขึ้นสำหรับ Mac M4 (0.4s)"""
        time.sleep(0.4) # เพิ่ม Delay เป็น 0.4 วินาทีเพื่อให้ชิป M4 ไม่ส่งคำสั่งเร็วเกินไป
        data, sw1, sw2 = connection.transmit(apdu)
        if sw1 == 0x61:
            data, sw1, sw2 = connection.transmit([0x00, 0xC0, 0x00, 0x00, sw2])
        return data, sw1, sw2

    def get_religion_deep_scan(self, connection):
        """ระบบสแกนหาศาสนาจากทุกตำแหน่งที่เป็นไปได้ (Scanner Mode)"""
        # ลองตำแหน่ง: 0xE2 (มาตรฐาน), 0x019A (รุ่นปี 60+), 0x011A (รุ่นบางล็อต)
        scan_offsets = [[0x00, 0xE2], [0x01, 0x9A], [0x01, 0x1A]]
        
        for off in scan_offsets:
            cmd = [0x80, 0xB0, off[0], off[1], 0x02, 0x00, 0x14]
            data, sw1, sw2 = self.send_apdu(connection, cmd)
            res = self.thai_decode(data)
            
            # กรองข้อมูล: ต้องมีภาษาไทย, ไม่ใช่ตัวเลข, และยาวกว่า 2 ตัวอักษร
            if res and not any(char.isdigit() for char in res) and len(res) >= 2:
                # ตรวจเช็คว่ามีคำที่เกี่ยวข้องกับศาสนาไหม (Optional)
                return res
        return "ไม่ระบุ/ไม่พบข้อมูล"

    def extract_birth_date(self, connection):
        """ระบบ Deep Scan ค้นหาวันเกิด"""
        try:
            cmd_scan = [0x80, 0xB0, 0x00, 0xD0, 0x02, 0x00, 0x20]
            data, sw1, sw2 = self.send_apdu(connection, cmd_scan)
            full_str = "".join(map(chr, data))
            match = re.search(r'(\d{8})', full_str)
            if match:
                dob = match.group(1)
                return f"{dob[6:8]}/{dob[4:6]}/{dob[0:4]}"
            return "N/A"
        except Exception:
            return "N/A"

    def update(self, observable, actions):
        (addedcards, removedcards) = actions
        for card in addedcards:
            print("\n" + "="*65)
            print("[+] ตรวจพบการเสียบบัตร... กำลังอ่านข้อมูล (M4 Deep Scan)")
            connection = card.createConnection()
            try:
                # ใช้ Warm Reset สำหรับ MacBook Air M4 และ macOS Tahoe
                connection.connect(disposition=1)
                self.send_apdu(connection, SELECT_APPLET)

                # ดึงข้อมูล
                cid_raw, _, _     = self.send_apdu(connection, CMD_CID)
                name_th_raw, _, _ = self.send_apdu(connection, CMD_NAME_TH)
                name_en_raw, _, _ = self.send_apdu(connection, CMD_NAME_EN)
                birth_date        = self.extract_birth_date(connection)
                gender_raw, _, _  = self.send_apdu(connection, CMD_GENDER)
                religion          = self.get_religion_deep_scan(connection)
                address_raw, _, _ = self.send_apdu(connection, CMD_ADDRESS)

                print("-" * 65)
                print(f"เลขบัตรประชาชน      : {''.join(map(chr, cid_raw))}")
                print(f"ชื่อ-นามสกุล (TH)    : {self.thai_decode(name_th_raw)}")
                print(f"ชื่อ-นามสกุล (EN)    : {''.join(map(chr, name_en_raw)).strip().replace('#', ' ')}")
                print(f"วันเดือนปีเกิด       : {birth_date}")
                print(f"เพศ                 : {'ชาย' if chr(gender_raw[0]) == '1' else 'หญิง'}")
                print(f"ศาสนา               : {religion}")
                print(f"ที่อยู่              : {self.thai_decode(address_raw)}")
                print("-" * 65)
                print("✅ อ่านข้อมูลสำเร็จ (Optimized for M4)")
                print("="*65)

            except Exception as e:
                print(f"⚠️ Error: {e}")
            finally:
                try: connection.disconnect()
                except: pass

        for card in removedcards:
            print("\n[-] บัตรถูกดึงออก")

if __name__ == '__main__':
    print("🚀 Thai ID Monitor Deep Scanner เริ่มทำงาน...")
    monitor = CardMonitor()
    observer = ThaiIDCardObserver()
    monitor.addObserver(observer)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        monitor.deleteObserver(observer)