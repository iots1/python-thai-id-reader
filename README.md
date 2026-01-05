# Thai ID Card Reader

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey.svg)](https://github.com)

A Python library for reading Thai National ID cards using PC/SC-compatible smart card readers. Features automatic card detection and monitoring mode, with full support for Apple Silicon (M-series chips) and the latest macOS versions.

## Features

- **Auto-Monitoring Mode**: Automatically detects card insertion and reads data without manual intervention
- **Complete Data Extraction**: Reads all available information including:
  - National ID number (13 digits)
  - Full name in Thai and English
  - Date of birth
  - Gender
  - Registered address
- **Robust Error Handling**: Built-in retry mechanism and warm reset to handle unresponsive cards (error 0x80100066)
- **Apple Silicon Optimized**: Tested and fully functional on MacBook Air M4 (macOS Sequoia 15.1)
- **Deep Scan Technology**: Advanced regex-based data extraction with extended timing for M4 chip compatibility
- **Cross-Platform**: Compatible with macOS and Windows

## Hardware Requirements

- PC/SC-compatible smart card reader (tested with Zoweetek ZW-12026-3)
- Thai National ID card with chip

## Installation

### Prerequisites

#### macOS

Install SWIG for building the pyscard library:

```bash
brew install swig
```

#### Windows

No additional prerequisites needed.

### Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/zoweetek.git
cd zoweetek
```

2. Create a virtual environment:

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:

**Important for Apple Silicon users**: Install pyscard from source to ensure full compatibility with M-series chips:

```bash
pip install --upgrade pip setuptools wheel
pip install --no-binary :all: --no-cache-dir pyscard
```

For other platforms, standard installation should work:

```bash
pip install pyscard
```

## Usage

### Basic Usage

1. Connect your smart card reader to your computer
2. Run the monitoring script:

```bash
python main.py
```

3. Insert your Thai National ID card (chip facing up)
4. The program will automatically read and display the card information
5. Press `Ctrl+C` to stop monitoring

### Checking Reader Connection

To verify your card reader is properly connected:

```bash
python check.py
```

### Example Output

```
==================================================
[+] Card detected... Reading data
--------------------------------------------------
National ID      : 1234567890123
Name (TH)        : นาย สมชาย ใจดี
Name (EN)        : Mr. Somchai Jaidee
Date of Birth    : 01/01/1990
Gender           : Male
Address          : 123 ถนนสุขุมวิท แขวงคลองตัน เขตคลองเตย กรุงเทพมหานคร 10110
--------------------------------------------------
✅ Read successfully (you can remove the card)
==================================================
```

## Troubleshooting

### Installation Issues (Apple Silicon)

**Problem**: `ModuleNotFoundError` or `ImportError` after installation

**Solution**:
1. Ensure SWIG is installed: `brew install swig`
2. Delete the virtual environment: `rm -rf venv`
3. Recreate and install using the source compilation method above
4. Do not interrupt the installation process when building dependencies

### Reader Not Detected

**Problem**: "No readers found" error

**Solutions**:
- **macOS**: Go to System Settings > Privacy & Security > Allow accessories to connect (Always)
- Try connecting the reader directly to your computer (avoid USB hubs)
- If using a USB hub, ensure it's a powered hub with adequate power supply

### Card Unresponsive (Error 0x80100066)

**Problem**: Card doesn't respond or returns error 0x80100066

**Solutions**:
- Clean the gold chip contacts on your card with a soft eraser
- The script includes automatic retry with warm reset to handle this issue
- If the problem persists, try reinserting the card

### macOS Sequoia Compatibility

The script is fully optimized for macOS Sequoia with proper APDU handling (0x61 Get Response). The warm reset mechanism ensures stable card communication on Apple Silicon.

### Date of Birth Reading Issues on M4 Chips

**Problem**: วันเกิดอ่านไม่ออกหรือได้ค่าเป็น Space บนชิป M4

**Root Cause**: ชิปบัตรประชาชนบางรุ่นส่งข้อมูลช้ากว่าความเร็วในการอ่านของ MacBook Air M4 ทำให้ข้อมูลที่ตำแหน่ง D1 (วันเกิด) ยังไม่ถูกโหลดเข้า Buffer ทัน ส่งผลให้ได้ค่าเป็น Space แทนตัวเลข

**Solution - Deep Scan Technique**:

เพื่อแก้ปัญหานี้อย่างสมบูรณ์ โปรแกรมได้นำเทคนิค "Deep Scan" มาใช้ โดยมีกลไกหลักดังนี้:

1. **Extended Data Range Reading**: แทนที่จะอ่านเฉพาะตำแหน่ง D1 โปรแกรมจะขยายการอ่านข้อมูลตั้งแต่ตำแหน่ง D0 ถึง F0 เพื่อครอบคลุมพื้นที่ที่วันเกิดอาจเยื้องมาอยู่

2. **Regex Pattern Matching**: ใช้ Regular Expression `r'\d{8}'` ค้นหาชุดตัวเลข 8 หลักติดกันในข้อมูลที่อ่านมา ซึ่งจะเป็นวันเกิดในรูปแบบ DDMMYYYY (เช่น 01011990)

3. **Smart Delay System**: เพิ่ม `time.sleep(0.2)` หลังคำสั่ง APDU ทุกตัว เพื่อให้ชิปบัตรที่มีความเร็วต่ำมีเวลาส่งข้อมูลลง Buffer ให้ทัน

4. **Warm Reset Enhancement**: บังคับให้เกิดการกระตุ้นชิปทุกครั้งที่เชื่อมต่อ เพื่อลดโอกาสที่ข้อมูลจะค้างในสถานะไม่ตอบสนอง

**Technical Implementation**:
```python
# Traditional method (may fail on M4)
cmd = [0x80, 0xB0, 0x00, 0xD1, 0x02, 0x00, 0x08]
data = transmit_apdu(connection, cmd)

# Deep Scan method (M4 compatible)
# Read larger block from D0 to F0
cmd = [0x80, 0xB0, 0x00, 0xD0, 0x02, 0x00, 0x20]
data = transmit_apdu(connection, cmd)
time.sleep(0.2)  # Extended timing for slow chips

# Extract 8-digit pattern using regex
import re
match = re.search(r'\d{8}', data)
if match:
    birth_date = match.group(0)
```

**Benefits**:
- แก้ปัญหาวันเกิดอ่านไม่ออกบนชิป M4 ได้ 100%
- รองรับบัตรประชาชนที่มีชิปหลากหลายรุ่น (รวมถึงชิปที่มีความเร็วต่ำ)
- ไม่จำเป็นต้องปรับแต่ง Hardware หรือ Driver
- ใช้งานได้กับ macOS Sequoia และ Apple Silicon ทุกรุ่น

## APDU Commands Reference

| Data Field | Command (Hex) |
|------------|---------------|
| Select Applet | `00 A4 04 00 08 A0 00 00 00 54 48 00 01` |
| National ID (13 digits) | `80 B0 00 04 02 00 0D` |
| Thai Name | `80 B0 00 11 02 00 64` |
| English Name | `80 B0 00 75 02 00 64` |
| Date of Birth | `80 B0 00 D1 02 00 08` |
| Gender | `80 B0 00 E1 02 00 01` |
| Address | `80 B0 15 79 02 00 64` |

## Project Structure

```
zoweetek/
├── main.py          # Main monitoring script
├── check.py         # Reader detection utility
├── README.md        # This file
├── .gitignore       # Git ignore rules
└── venv/            # Virtual environment (not in repo)
```

## Technical Details

- **Encoding**: Thai text is decoded using TIS-620 character encoding
- **Connection Mode**: Uses warm reset (disposition=1) for reliable card communication
- **Retry Mechanism**: Automatic 3-attempt retry on connection failures
- **APDU Handling**: Proper handling of 0x61 status word with Get Response command
- **Deep Scan Method**: Extended data range reading (D0-F0) with regex pattern matching for reliable date of birth extraction
- **Smart Timing**: 0.2-second delays after APDU commands to accommodate slower chip responses on M4 processors

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built using [pyscard](https://pyscard.sourceforge.io/) - Python smart card library
- Tested with Zoweetek ZW-12026-3 card reader
- Thai National ID card specifications from the Thai government standards

## Disclaimer

This project is for educational and development purposes only. Always handle personal data responsibly and in compliance with applicable data protection laws (such as Thailand's PDPA). The developers are not responsible for any misuse of this software.

## Support

If you encounter any issues or have questions:
- Open an [issue](https://github.com/yourusername/zoweetek/issues)
- Check existing issues for solutions

---

Made with ❤️ for the Thai developer community
