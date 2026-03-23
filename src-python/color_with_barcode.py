import cv2
import numpy as np
import csv
import os
import threading
from datetime import datetime

# --- 1. ตั้งค่าตำแหน่งไฟล์ (ให้เซฟที่เดียวกับไฟล์ camera.py) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
filename = os.path.join(current_dir, "scanned_data.csv")

def save_to_csv(barcode, color):
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # ถ้ายังไม่มีไฟล์ ให้สร้างหัวตาราง (Header)
        if not file_exists:
            writer.writerow(["Time", "Barcode", "Color"])
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([current_time, barcode, color])
    print(f"\n💾 [บันทึกสำเร็จ] บาร์โค้ด: {barcode} | สี: {color}")
    print(f"📍 ไฟล์อยู่ที่: {filename}")

# --- 2. ฟังก์ชันวิเคราะห์สีในกรอบ ---
def get_color_name(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # ช่วงสี HSV (ปรับจูนตามแสงในห้องได้)
    color_ranges = {
        "Red": [([0, 150, 70], [10, 255, 255]), ([170, 150, 70], [180, 255, 255])],
        "Green": [([40, 70, 70], [85, 255, 255])],
        "Blue": [([100, 150, 50], [140, 255, 255])]
    }
    
    for name, ranges in color_ranges.items():
        mask = np.zeros(hsv.shape[:2], dtype="uint8")
        for (l, u) in ranges:
            mask = cv2.add(mask, cv2.inRange(hsv, np.array(l), np.array(u)))
        
        # ถ้าพบสีเกิน 10% ของพื้นที่กรอบ
        if cv2.countNonZero(mask) > (roi.shape[0] * roi.shape[1] * 0.1):
            return name
    return "None"

# --- 3. ระบบ Threading รอรับค่าจากเครื่องสแกน (Background Process) ---
current_detected_color = "None"
is_running = True

def barcode_listener():
    global current_detected_color, is_running
    print(f"--- ระบบพร้อมรับค่าจากเครื่องสแกนแล้ว ---")
    while is_running:
        try:
            # เครื่องสแกนจะส่งตัวเลข + Enter มาที่นี่
            barcode_data = input().strip() 
            if barcode_data:
                # ตรวจสอบว่าขณะยิง สีกำลังถูกต้องหรือไม่
                if current_detected_color in ["Red", "Green", "Blue"]:
                    save_to_csv(barcode_data, current_detected_color)
                else:
                    print(f"\n❌ [ปฏิเสธ] สีไม่ถูกต้อง ({current_detected_color}) กรุณาวางสินค้าในกรอบเขียวก่อนยิง")
        except EOFError:
            break

# เริ่มต้น Thread เพื่อไม่ให้ input() ไปหยุดการทำงานของกล้อง
listener_thread = threading.Thread(target=barcode_listener, daemon=True)
listener_thread.start()

# --- 4. เริ่มการทำงานของกล้อง ---
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # กำหนดพื้นที่กรอบตรวจจับ (ROI) ตรงกลางหน้าจอ
    h, w, _ = frame.shape
    x1, y1, x2, y2 = w//3, h//3, (w//3)*2, (h//3)*2
    roi = frame[y1:y2, x1:x2]
    
    # วิเคราะห์สีปัจจุบัน
    current_detected_color = get_color_name(roi)
    
    # เช็คเงื่อนไขสี (ถ้าใช่กรอบจะสีเขียว)
    is_valid = current_detected_color in ["Red", "Green", "Blue"]
    status_color = (0, 255, 0) if is_valid else (0, 0, 255)
    
    # วาดหน้าจอ UI
    cv2.rectangle(frame, (x1, y1), (x2, y2), status_color, 3)
    cv2.putText(frame, f"STATUS: {current_detected_color}", (x1, y1-15), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    
    # คำแนะนำ
    hint = "READY TO SCAN" if is_valid else "WAITING FOR COLOR..."
    cv2.putText(frame, hint, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
    
    cv2.imshow("Smart Scanner (Documents/kim/)", frame)

    # กด 'q' เพื่อปิดโปรแกรม
    if cv2.waitKey(1) & 0xFF == ord('q'):
        is_running = False
        break

cap.release()
cv2.destroyAllWindows()
print(f"\n--- ปิดโปรแกรมเรียบร้อย ข้อมูลอยู่ใน scanned_data.csv ---")

