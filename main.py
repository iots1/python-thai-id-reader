import time
import re
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import toBytes
from smartcard.Exceptions import CardConnectionException

# --- ชุดคำสั่ง APDU สำหรับข้อมูลทั้งหมด ---
SELECT_APPLET = [0x00, 0xA4, 0x04, 0x00, 0x08, 0xA0, 0x00, 0x00, 0x00, 0x54, 0x48, 0x00, 0x01]
CMD_CID       = [0x80, 0xB0, 0x00, 0x04, 0x02, 0x00, 0x0D]
CMD_NAME_TH   = [0x80, 0xB0, 0x00, 0x11, 0x02, 0x00, 0x64]
CMD_NAME_EN   = [0x80, 0xB0, 0x00, 0x75, 0x02, 0x00, 0x64]
CMD_ADDRESS   = [0x80, 0xB0, 0x15, 0x79, 0x02, 0x00, 0x64]
CMD_GENDER    = [0x80, 0xB0, 0x00, 0xE1, 0x02, 0x00, 0x01] # เพศ
CMD_RELIGION  = [0x80, 0xB0, 0x00, 0xE2, 0x02, 0x00, 0x14] # ศาสนา (ปรับจาก D9 เป็น E2)

class ThaiIDCardObserver(CardObserver):
    def thai_decode(self, data):
        """แปลงรหัสภาษาไทย TIS-620"""
        try:
            return bytes(data).decode('tis-620').strip().replace('#', ' ')
        except Exception:
            return "N/A"

    def english_decode(self, data):
        """แปลงข้อมูลภาษาอังกฤษและแทนที่ # เป็น space"""
        try:
            return ''.join(map(chr, data)).strip().replace('#', ' ')
        except Exception:
            return "N/A"

    def send_apdu(self, connection, apdu):
        """ส่งคำสั่งพร้อมหน่วงเวลาเพื่อให้ชิป M4 และ Tahoe เสถียร"""
        time.sleep(0.2) 
        data, sw1, sw2 = connection.transmit(apdu)
        if sw1 == 0x61:
            data, sw1, sw2 = connection.transmit([0x00, 0xC0, 0x00, 0x00, sw2])
        return data, sw1, sw2

    def extract_birth_date(self, connection):
        """ระบบ Deep Scan ค้นหาวันเกิดอัตโนมัติ"""
        try:
            cmd_scan = [0x80, 0xB0, 0x00, 0xD0, 0x02, 0x00, 0x20]
            data, sw1, sw2 = self.send_apdu(connection, cmd_scan)
            full_str = "".join(map(chr, data))
            match = re.search(r'(\d{8})', full_str)
            if match:
                dob = match.group(1)
                return f"{dob[6:8]}/{dob[4:6]}/{dob[0:4]}"
            return "ไม่พบข้อมูล"
        except:
            return "Error Reading Birth Date"

    def update(self, observable, actions):
        (addedcards, removedcards) = actions
        for card in addedcards:
            print("\n" + "="*60)
            print("[+] ตรวจพบการเสียบบัตร... กำลังอ่านข้อมูล")
            
            connection = card.createConnection()
            try:
                # ใช้ Warm Reset แก้ปัญหา Unresponsive บน MacBook Air M4
                connection.connect(disposition=1)
                self.send_apdu(connection, SELECT_APPLET)

                # ดึงข้อมูล
                cid_raw, _, _      = self.send_apdu(connection, CMD_CID)
                name_th_raw, _, _  = self.send_apdu(connection, CMD_NAME_TH)
                name_en_raw, _, _  = self.send_apdu(connection, CMD_NAME_EN)
                birth_date         = self.extract_birth_date(connection)
                gender_raw, _, _   = self.send_apdu(connection, CMD_GENDER)
                religion_raw, _, _ = self.send_apdu(connection, CMD_RELIGION)
                address_raw, _, _  = self.send_apdu(connection, CMD_ADDRESS)

                gender = "ชาย" if chr(gender_raw[0]) == '1' else "หญิง"

                print("-" * 60)
                print(f"เลขบัตรประชาชน      : {''.join(map(chr, cid_raw))}")
                print(f"ชื่อ-นามสกุล (TH)    : {self.thai_decode(name_th_raw)}")
                print(f"ชื่อ-นามสกุล (EN)    : {self.english_decode(name_en_raw)}")
                print(f"วันเดือนปีเกิด       : {birth_date}")
                print(f"เพศ                 : {gender}")
                print(f"ศาสนา               : {self.thai_decode(religion_raw)}")
                print(f"ที่อยู่              : {self.thai_decode(address_raw)}")
                print("-" * 60)
                print("✅ อ่านข้อมูลสำเร็จ (Optimized for M4 & Tahoe)")
                print("="*60)

            except Exception as e:
                print(f"⚠️ Error: {e}")
            finally:
                try: connection.disconnect()
                except: pass

        for card in removedcards:
            print("\n[-] บัตรถูกดึงออก... รอรับบัตรใบใหม่")

if __name__ == '__main__':
    print("🚀 ระบบ Smart Card Monitor (Thai ID) เริ่มทำงาน...")
    print("   รองรับชิป M4 และ macOS Tahoe 26.1")
    monitor = CardMonitor()
    observer = ThaiIDCardObserver()
    monitor.addObserver(observer)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        monitor.deleteObserver(observer)