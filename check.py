import smartcard.System
from smartcard.scard import *

try:
    readers = smartcard.System.readers()
    print(f"--- ผลการตรวจสอบ ---")
    if not readers:
        print("❌ ระบบยังมองไม่เห็นเครื่องอ่าน")
        print("คำแนะนำ: ตรวจสอบสาย USB หรือลองใช้ USB Hub ที่มีไฟเลี้ยง (Powered Hub)")
    else:
        for r in readers:
            print(f"✅ พบเครื่องอ่าน: {r}")
except Exception as e:
    print(f"เกิดข้อผิดพลาด: {e}")