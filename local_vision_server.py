import json
import sys
import base64
import os
import hashlib
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

class DynamicVisionServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))
        sys.stdout.flush()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        messages = data.get('messages', [])
        prompt_text = ""
        images_found = []

        for m in messages:
            content = m.get('content', '')
            if isinstance(content, list):
                for part in content:
                    if part.get('type') == 'text':
                        prompt_text += part.get('text', '')
                    elif part.get('type') == 'image_url':
                        url = part.get('image_url', {}).get('url', '')
                        if url.startswith('data:image'):
                            # Extract base64
                            try:
                                b64 = url.split(',', 1)[1]
                                images_found.append(base64.b64decode(b64))
                            except Exception:
                                pass
            elif isinstance(content, str):
                prompt_text += content

        timestamp = datetime.now().strftime("%H%M%S")

        # 1. OCR Request
        if "FRONT of a government-issued ID" in prompt_text:
            img_info = "No image found"
            img_hash = "0000"
            if images_found:
                # Save the real uploaded ID image to disk so you can verify it
                saved_path = f"captured_id_front_{timestamp}.jpg"
                with open(saved_path, "wb") as f:
                    f.write(images_found[0])
                img_size = len(images_found[0])
                img_hash = hashlib.md5(images_found[0]).hexdigest()[:6].upper()
                img_info = f"Saved {saved_path} ({img_size} bytes, hash: {img_hash})"
            
            print(f"[OCR REQUEST] Image processed: {img_info}")

            # Dynamic field generation based on image hash to verify DIFFERENT images produce DIFFERENT results!
            result = {
                "isDocumentDetected": True,
                "documentType": "DRIVERS_LICENSE",
                "issuingJurisdiction": "CA",
                "issuingState": "CA",
                "documentNumber": f"DL-{img_hash}",
                "firstName": f"SUBMITTER_{img_hash[:3]}",
                "middleName": "",
                "lastName": f"ID_{img_hash[3:]}",
                "dateOfBirth": "1996-08-20",
                "issueDate": "2022-01-15",
                "expirationDate": "2029-08-20",
                "address": f"{int(img_hash, 16) % 900 + 100} CAPTURE BLVD",
                "addressLine1": f"{int(img_hash, 16) % 900 + 100} CAPTURE BLVD",
                "city": "ADDIS ABABA",
                "state": "AA",
                "stateProvince": "AA",
                "postalCode": "1000",
                "isRealId": True,
                "isCommercialDriversLicense": False,
                "isVeteran": False,
                "isDonor": True,
                "isLimitedDurationDocument": False,
                "isInvalidated": False,
                "isNonDomicile": False,
                "isEnhancedCredential": True,
                "isPermit": False,
                "isInterlockRestricted": False,
                "isSampleDocument": False,
                "extractionConfidence": 98,
                "qualityNotes": f"Real image verified (Hash: {img_hash})",
                "tamperNotes": None
            }

        # 2. Face Match Request
        else:
            if len(images_found) >= 2:
                saved_selfie = f"captured_selfie_{timestamp}.jpg"
                with open(saved_selfie, "wb") as f:
                    f.write(images_found[1])
                print(f"[FACE MATCH] Saved {saved_selfie} ({len(images_found[1])} bytes)")
            
            result = {
                "matchStatus": "MATCH",
                "matchConfidence": 95,
                "falseAcceptanceRate": "<0.01%",
                "assessedAgeFromSelfie": 28,
                "assessedAgeFromDocument": 28,
                "isAgeCheckSuccess": True,
                "isGenderCheckSuccess": True,
                "isSuspiciousPhoto": False,
                "antiSpoofingConfidence": 99,
                "isDataFieldsTampered": False,
                "isPhotoFromDocumentTampered": False,
                "aiNotes": "Selfie and document images analyzed."
            }

        response = {
            "id": "chatcmpl-dynamic-vision",
            "object": "chat.completion",
            "created": 1729278000,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(result)
                },
                "finish_reason": "stop"
            }]
        }

        response_bytes = json.dumps(response).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

def run():
    port = 8001
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, DynamicVisionServerHandler)
    print(f"============================================================")
    print(f" Dynamic Local Vision Server on http://localhost:{port}")
    print(f" Real captured images will be saved as .jpg in current folder!")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")

if __name__ == '__main__':
    run()
