import cv2
import mediapipe as mp
import numpy as np
import os
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from discord_helper import DiscordMemeTracker
import winsound

model_path = 'face_landmarker.task'

# ตรวจสอบว่ามีไฟล์โมเดลไหม ถ้าไม่มีจะแจ้งเตือน
if not os.path.exists(model_path):
    print(f"Error: ไม่พบไฟล์ {model_path} กรุณาดาวน์โหลดมาวางในโฟลเดอร์ก่อนรัน")
    exit()

base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=True,
    output_facial_transformation_matrixes=True, # แก้ชื่อตัวแปรตรงนี้ครับ
    num_faces=1
)

# สร้างตัวตรวจจับ (Detector)
detector = vision.FaceLandmarker.create_from_options(options)

# --- 2. ฟังก์ชันวิเคราะห์ใบหน้า (Thresholds) ---
eye_opening_threshold = 0.024
mouth_open_threshold = 0.035
squinting_threshold = 0.016      
mouth_pucker_threshold = 0.040
pucker_ratio_threshold = 0.28
erk_mouth_diff = 0.012   
erk_eye_squint = 0.025
smile_teeth_width_ratio = 0.38  # ปากต้องกว้างกว่า 38% ของใบหน้า
smile_teeth_gap = 0.015  


def cat_shock(face_points):
    """ ตรวจสอบอาการตาค้าง/เบิกตา (Shock) """
    l_top, l_bot = face_points[159], face_points[145]
    r_top, r_bot = face_points[386], face_points[374]
    
    # คำนวณความกว้างเฉลี่ยของตาสองข้าง
    eye_opening = (abs(l_top.y - l_bot.y) + abs(r_top.y - r_bot.y)) / 2.0
    
    return eye_opening > eye_opening_threshold

def cat_tongue(face_points):
    """ ตรวจสอบการอ้าปาก/แลบลิ้น (Tongue) """
    mouth_open = abs(face_points[13].y - face_points[14].y)
    return mouth_open > mouth_open_threshold

def cat_glare(face_points):
    l_top, l_bot = face_points[159], face_points[145]
    r_top, r_bot = face_points[386], face_points[374]
    eye_squint = (abs(l_top.y - l_bot.y) + abs(r_top.y - r_bot.y)) / 2.0
    
    # เช็กว่าปากขยับยิ้มหรือเปล่า
    mouth_lift = ((face_points[0].y - face_points[61].y) + (face_points[0].y - face_points[291].y)) / 2.0
    
    # คืนค่า True ถ้า "หรี่ตา" และ "ไม่ได้ยิ้ม"
    return eye_squint < squinting_threshold and mouth_lift < 0.005

def cat_smirk(face_points):
    mouth_width = abs(face_points[61].x - face_points[291].x)
    face_width = abs(face_points[234].x - face_points[454].x)
    width_ratio = mouth_width / face_width
    
    # 2. วัดระยะห่างริมฝีปากบน-ล่าง (จุด 13 และ 14)
    mouth_gap = abs(face_points[13].y - face_points[14].y)
    
    # 3. เช็กความสมมาตร (เพื่อไม่ให้ไปทับกับพี่เอิร์ก)
    mouth_diff = abs((face_points[0].y - face_points[61].y) - (face_points[0].y - face_points[291].y))

    # คืนค่า True ถ้า ปากกว้าง + มีช่องว่าง + ไม่เบี้ยวเกินไป (สมมาตร)
    return width_ratio > smile_teeth_width_ratio and mouth_gap > smile_teeth_gap and mouth_diff < 0.010

def cat_wow(face_points):
    """ ตรวจอาการ 'ยิ้มปริ่มปากจู๋' (เหมือนรูป cat-wow) 
        Logic: ตาโต + ความกว้างปากแนวนอนแคบลง
    """
    mouth_width = abs(face_points[61].x - face_points[291].x)
    
    # 2. วัดความกว้างใบหน้า (ใช้จุดโหนกแก้ม 234 ถึง 454)
    face_width = abs(face_points[234].x - face_points[454].x)
    
    # 3. คำนวณหาอัตราส่วน
    current_ratio = mouth_width / face_width 
    is_eye_wide = cat_shock(face_points)
    return current_ratio < pucker_ratio_threshold

def cat_erk(face_points):
    mouth_diff = abs(face_points[61].y - face_points[291].y)
    # เช็กตาหรี่ด้วย
    l_eye = abs(face_points[159].y - face_points[145].y)
    r_eye = abs(face_points[386].y - face_points[374].y)
    avg_eye = (l_eye + r_eye) / 2.0
    
    return mouth_diff > erk_mouth_diff and avg_eye < erk_eye_squint

def main():
    cam = cv2.VideoCapture(0)
    webhook_url = "ใส่ web hook discrod"
    discord_bot = DiscordMemeTracker(webhook_url)

    while cam.isOpened():
        ret, frame = cam.read()
        if not ret: break

        frame = cv2.flip(frame, 1) # กลับด้านภาพเหมือนกระจก
        h, w, _ = frame.shape

        # --- 3. การเตรียมภาพสำหรับ MediaPipe Tasks ---
        # ต้องแปลง BGR (OpenCV) เป็น RGB และสร้าง mp.Image object
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        # ทำการตรวจจับ (แบบ Sync)
        detection_result = detector.detect(mp_image)
        cat_image_path = "assets/larry.jpeg" # รูปเริ่มต้น (Larry)

        # --- 4. ตรวจสอบผลลัพธ์และวิเคราะห์ Logic ---
        if detection_result.face_landmarks:
            # ดึงจุด landmarks ของใบหน้าแรกที่เจอ
            face_points = detection_result.face_landmarks[0]

            # สร้างตัวแปรเก็บภาพก่อนหน้าเพื่อเช็คว่าเปลี่ยนท่าหรือยัง
            prev_image_path = cat_image_path

            if cat_erk(face_points):
                cat_image_path = "assets/cat-erk.jpg"
            #  ตามด้วยท่าปากจู๋
            elif cat_wow(face_points):
                cat_image_path = "assets/cat-wow.jpg"  
            # ท่าอ้าปาก
            elif cat_tongue(face_points):
                cat_image_path = "assets/cat-tongue.jpeg"     
            # ท่าตาโต
            elif cat_shock(face_points):
                cat_image_path = "assets/cat-shock.jpeg"

            # ท่าหรี่ตา 
            elif cat_glare(face_points):
                cat_image_path = "assets/cat-glare.jpeg"   
            # ท่ายิ้ม
            elif cat_smirk(face_points):
                cat_image_path = "assets/cat-smirk.jpg"
            else:
                cat_image_path = "assets/larry.jpeg"

            # ถ้าภาพเปลี่ยน (ท่าทางเปลี่ยน) ให้เล่นเสียง 1 ครั้ง
            if cat_image_path != prev_image_path and cat_image_path != "assets/larry.jpeg":
                winsound.PlaySound("assets/meow.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)

        discord_bot.check_and_send(cat_image_path)
        # --- 5. การแสดงผล (Display) ---
        cv2.imshow('Face Detection (Original)', frame)

        # อ่านและแสดงรูปมีมแมว
        cat_img = cv2.imread(cat_image_path)
        if cat_img is not None:
            cat_img = cv2.resize(cat_img, (640, 480))
            cv2.imshow("Meme Display", cat_img)
        else:
            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(blank, f"File Missing: {cat_image_path}", (50, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.imshow("Meme Display", blank)
        
        if cv2.waitKey(1) & 0xFF == 27: 
            break

    cam.release()
    cv2.destroyAllWindows()



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] ปิดโปรแกรมโดยผู้ใช้งาน (MeowCV Stopped)")
        try:
            import cv2
            cv2.destroyAllWindows()
        except:
            pass