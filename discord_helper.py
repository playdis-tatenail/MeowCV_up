import time
import requests
import os

class DiscordMemeTracker:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.current_meme = "assets/larry.jpeg"
        self.start_time = time.time()
        self.already_sent = False
        self.wait_time = 1.5

        self.meme_captions = {
            "assets/cat-erk.jpg": "เสร็จตรูแน่ ระวังไว้เถอะ  💅",
            "assets/cat-wow.jpg": "เห้ยทำไรอ่ะ บ้าบออออ 😲",
            "assets/cat-tongue.jpeg": "แบร่! ตกใจปะจ๊ะ ล้อเล่นจ้า😝",
            "assets/cat-shock.jpeg": "ถามจริ๊งงงงงง เอาจริงดิ! 🙀",
            "assets/cat-glare.jpeg": "อ่อ อิม เริดเลยเนอะ better only u! 😼",
            "assets/cat-smirk.jpg": "ยิ้มไรอ่ะ เขิลลล 😏"
        }
    def check_and_send(self, new_meme_path):
        if new_meme_path != self.current_meme:
            self.current_meme = new_meme_path
            self.start_time = time.time()
            self.already_sent = False
            return

        if self.current_meme != "assets/larry.jpeg" and not self.already_sent:
            elapsed_time = time.time() - self.start_time
            if elapsed_time > self.wait_time:
                # ดึง Caption ออกมา ถ้าไม่มีให้ใช้ข้อความ Default
                caption = self.meme_captions.get(self.current_meme, "ส่งรูปมีมสุดปังมาฝากจ้า! ✨")
                self._send_image(self.current_meme, caption)
                self.already_sent = True

    def _send_image(self, image_path, caption): # เพิ่ม parameter caption
        if not os.path.exists(image_path):
            print(f"[Discord] ไม่พบไฟล์: {image_path}")
            return

        try:
            with open(image_path, 'rb') as f:
                # ใช้ caption ที่ส่งมาใส่ใน content
                payload = {"content": caption} 
                files = {"file": f}
                response = requests.post(self.webhook_url, data=payload, files=files)
                
                if response.status_code in [200, 204]:
                    print(f"✅ [Discord] ส่งรูปพร้อม Caption สำเร็จ!")
                else:
                    print(f"❌ [Discord] ส่งไม่สำเร็จ: {response.status_code}")
        except Exception as e:
            print(f"⚠️ [Discord] Error: {e}")