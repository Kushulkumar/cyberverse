from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
import requests
import socket
import whois
import ssl
from datetime import datetime
from urllib.parse import urlparse
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import tempfile
from werkzeug.utils import secure_filename
import io
import wave
import array
import struct
import zlib
import random

# Try to import additional modules for steganography
try:
    from PIL import Image
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not installed. Image steganography will be limited.")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("OpenCV not installed. Video steganography will be disabled.")

# Crypto imports
try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    from Crypto.Protocol.KDF import PBKDF2 as CryptoPBKDF2
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Crypto not installed. Using fallback encryption.")

app = Flask(__name__,
            static_folder='frontend/static',
            template_folder='frontend')
app.config['SECRET_KEY'] = 'cyberverse_secure_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cyberverse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
CORS(app)

# ===================== DATABASE MODELS =====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    score = db.Column(db.Integer)
    total = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ===================== ADVANCED STEGANOGRAPHY CLASSES =====================

class SecurityLayer:
    @staticmethod
    def compress_data(data):
        """Compress data with error handling"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            return zlib.compress(data, level=6)
        except Exception as e:
            print(f"Compression error: {e}")
            return data if isinstance(data, bytes) else data.encode('utf-8')

    @staticmethod
    def decompress_data(data):
        """Decompress data with error handling"""
        try:
            return zlib.decompress(data)
        except:
            return data

    @staticmethod
    def derive_key(password, salt):
        """Derive encryption key from password"""
        if CRYPTO_AVAILABLE:
            return CryptoPBKDF2(password, salt, dkLen=32, count=100000)
        else:
            import hashlib
            return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, dkLen=32)

    @staticmethod
    def encrypt_aes(data, password):
        """Encrypt data with AES-GCM"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')

            salt = get_random_bytes(16)
            key = SecurityLayer.derive_key(password, salt)

            if CRYPTO_AVAILABLE:
                cipher = AES.new(key, AES.MODE_GCM)
                ciphertext, tag = cipher.encrypt_and_digest(data)
                return salt + cipher.nonce + tag + ciphertext
            else:
                from cryptography.fernet import Fernet
                import base64
                key_b64 = base64.urlsafe_b64encode(key[:32])
                fernet = Fernet(key_b64)
                encrypted = fernet.encrypt(data)
                return salt + encrypted
        except Exception as e:
            print(f"Encryption error: {e}")
            raise

    @staticmethod
    def decrypt_aes(encrypted_data, password):
        """Decrypt data with AES-GCM"""
        try:
            if len(encrypted_data) < 48:
                raise ValueError("Encrypted data too short")

            salt = encrypted_data[:16]
            key = SecurityLayer.derive_key(password, salt)

            if CRYPTO_AVAILABLE:
                nonce = encrypted_data[16:32]
                tag = encrypted_data[32:48]
                ciphertext = encrypted_data[48:]
                cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                return cipher.decrypt_and_verify(ciphertext, tag)
            else:
                from cryptography.fernet import Fernet
                import base64
                key_b64 = base64.urlsafe_b64encode(key[:32])
                fernet = Fernet(key_b64)
                return fernet.decrypt(encrypted_data[16:])
        except Exception as e:
            print(f"Decryption error: {e}")
            raise

    @staticmethod
    def process_encode(payload, password):
        """Complete encoding process"""
        try:
            compressed = SecurityLayer.compress_data(payload)
            encrypted = SecurityLayer.encrypt_aes(compressed, password)
            return encrypted
        except Exception as e:
            print(f"Process encode error: {e}")
            raise

    @staticmethod
    def process_decode(encrypted_data, password):
        """Complete decoding process"""
        try:
            decrypted = SecurityLayer.decrypt_aes(encrypted_data, password)
            decompressed = SecurityLayer.decompress_data(decrypted)
            return decompressed
        except Exception as e:
            print(f"Process decode error: {e}")
            raise


class ImageSteganography:
    @staticmethod
    def encode_lsb(carrier_bytes, payload_bytes):
        """Encode payload into image using LSB"""
        if not PIL_AVAILABLE:
            raise ValueError("PIL library not available")

        try:
            img = Image.open(io.BytesIO(carrier_bytes)).convert('RGB')
            pixels = np.array(img)
            flat_pixels = pixels.flatten()

            payload_binary = ''.join(format(byte, '08b') for byte in payload_bytes)
            payload_length = len(payload_binary)

            length_binary = format(payload_length, '032b')
            full_binary = length_binary + payload_binary

            if len(full_binary) > len(flat_pixels):
                max_bytes = (len(flat_pixels) - 32) // 8
                raise ValueError(f"Payload too large! Max {max_bytes} bytes")

            for i, bit in enumerate(full_binary):
                flat_pixels[i] = (flat_pixels[i] & 0xFE) | int(bit)

            stego_pixels = flat_pixels.reshape(pixels.shape)
            stego_img = Image.fromarray(stego_pixels.astype('uint8'), 'RGB')

            output_bytes = io.BytesIO()
            stego_img.save(output_bytes, format='PNG')
            return output_bytes.getvalue()
        except Exception as e:
            print(f"Image encode error: {e}")
            raise

    @staticmethod
    def decode_lsb(stego_bytes):
        """Extract payload from image using LSB"""
        if not PIL_AVAILABLE:
            raise ValueError("PIL library not available")

        try:
            img = Image.open(io.BytesIO(stego_bytes))
            pixels = np.array(img)
            flat_pixels = pixels.flatten()

            length_binary = ''
            for i in range(32):
                length_binary += str(flat_pixels[i] & 1)
            payload_length = int(length_binary, 2)

            if payload_length > len(flat_pixels) * 8:
                raise ValueError("Invalid payload length")

            payload_binary = ''
            for i in range(32, min(32 + payload_length, len(flat_pixels))):
                payload_binary += str(flat_pixels[i] & 1)

            payload_bytes = bytearray()
            for i in range(0, len(payload_binary), 8):
                if i + 8 <= len(payload_binary):
                    byte = int(payload_binary[i:i+8], 2)
                    payload_bytes.append(byte)

            return bytes(payload_bytes)
        except Exception as e:
            print(f"Image decode error: {e}")
            raise


class AudioSteganography:
    @staticmethod
    def encode_wav(carrier_bytes, payload_bytes):
        """Encode payload into WAV audio file"""
        try:
            temp_input = io.BytesIO(carrier_bytes)
            temp_output = io.BytesIO()

            with wave.open(temp_input, 'rb') as wav_in:
                params = wav_in.getparams()
                frames = wav_in.readframes(params.nframes)

                sample_width = params.sampwidth

                if sample_width == 1:
                    fmt = f"{len(frames)}B"
                    samples = list(struct.unpack(fmt, frames))
                elif sample_width == 2:
                    fmt = f"{len(frames)//2}h"
                    samples = list(struct.unpack(fmt, frames))
                else:
                    raise ValueError(f"Unsupported sample width: {sample_width}")

                payload_binary = ''.join(format(byte, '08b') for byte in payload_bytes)
                payload_length = len(payload_binary)

                length_binary = format(payload_length, '032b')
                full_binary = length_binary + payload_binary

                if len(full_binary) > len(samples):
                    max_bytes = (len(samples) - 32) // 8
                    raise ValueError(f"Payload too large! Max {max_bytes} bytes")

                for i, bit in enumerate(full_binary):
                    samples[i] = (samples[i] & 0xFE) | int(bit)

                if sample_width == 1:
                    output_frames = struct.pack(fmt, *samples)
                else:
                    output_frames = struct.pack(fmt, *samples)

                with wave.open(temp_output, 'wb') as wav_out:
                    wav_out.setparams(params)
                    wav_out.writeframes(output_frames)

            return temp_output.getvalue()
        except Exception as e:
            print(f"Audio encode error: {e}")
            raise

    @staticmethod
    def decode_wav(stego_bytes):
        """Extract payload from WAV audio file"""
        try:
            temp_input = io.BytesIO(stego_bytes)

            with wave.open(temp_input, 'rb') as wav_in:
                params = wav_in.getparams()
                frames = wav_in.readframes(params.nframes)

                sample_width = params.sampwidth

                if sample_width == 1:
                    fmt = f"{len(frames)}B"
                    samples = list(struct.unpack(fmt, frames))
                elif sample_width == 2:
                    fmt = f"{len(frames)//2}h"
                    samples = list(struct.unpack(fmt, frames))
                else:
                    raise ValueError(f"Unsupported sample width: {sample_width}")

                length_binary = ''
                for i in range(32):
                    if i < len(samples):
                        length_binary += str(samples[i] & 1)

                payload_length = int(length_binary, 2)

                if payload_length > len(samples) * 8:
                    raise ValueError("Invalid payload length")

                payload_binary = ''
                for i in range(32, min(32 + payload_length, len(samples))):
                    payload_binary += str(samples[i] & 1)

                payload_bytes = bytearray()
                for i in range(0, len(payload_binary), 8):
                    if i + 8 <= len(payload_binary):
                        byte = int(payload_binary[i:i+8], 2)
                        payload_bytes.append(byte)

                return bytes(payload_bytes)
        except Exception as e:
            print(f"Audio decode error: {e}")
            raise


class TextSteganography:
    @staticmethod
    def encode_text(carrier_bytes, payload_bytes):
        """Encode payload into text file (append with marker)"""
        try:
            marker = b'\n===STEGO_V2===\n'
            length_header = struct.pack('>I', len(payload_bytes))
            return carrier_bytes + marker + length_header + payload_bytes
        except Exception as e:
            print(f"Text encode error: {e}")
            raise

    @staticmethod
    def decode_text(stego_bytes):
        """Extract payload from text file"""
        try:
            marker = b'\n===STEGO_V2===\n'
            marker_pos = stego_bytes.rfind(marker)

            if marker_pos != -1:
                length_pos = marker_pos + len(marker)
                if length_pos + 4 <= len(stego_bytes):
                    payload_length = struct.unpack('>I', stego_bytes[length_pos:length_pos+4])[0]
                    payload_start = length_pos + 4
                    if payload_start + payload_length <= len(stego_bytes):
                        return stego_bytes[payload_start:payload_start+payload_length]

            raise ValueError("No steganographic data found in text file")
        except Exception as e:
            print(f"Text decode error: {e}")
            raise


# ===================== STEGANOGRAPHY ROUTES =====================

@app.route('/embed', methods=['POST'])
def embed():
    try:
        carrier_file = request.files['carrier']
        payload_text = request.form.get('payloadText', '')
        password = request.form.get('password')
        file_type = request.form.get('fileType')

        if not payload_text or not password or not file_type:
            return jsonify({'error': 'All fields are required!'}), 400

        carrier_bytes = carrier_file.read()
        filename = secure_filename(carrier_file.filename)

        encrypted_payload = SecurityLayer.process_encode(payload_text.encode('utf-8'), password)

        marker = b'STEGO_V2'
        payload_with_marker = marker + struct.pack('>I', len(encrypted_payload)) + encrypted_payload

        if file_type == 'image':
            stego_bytes = ImageSteganography.encode_lsb(carrier_bytes, payload_with_marker)
            return send_file(
                io.BytesIO(stego_bytes),
                as_attachment=True,
                download_name='stego_image.png',
                mimetype='image/png'
            )

        elif file_type == 'audio':
            stego_bytes = AudioSteganography.encode_wav(carrier_bytes, payload_with_marker)
            return send_file(
                io.BytesIO(stego_bytes),
                as_attachment=True,
                download_name='stego_audio.wav',
                mimetype='audio/wav'
            )

        elif file_type == 'text':
            stego_bytes = TextSteganography.encode_text(carrier_bytes, payload_with_marker)
            return send_file(
                io.BytesIO(stego_bytes),
                as_attachment=True,
                download_name='stego_text.txt',
                mimetype='text/plain'
            )

        else:
            stego_bytes = carrier_bytes + payload_with_marker
            return send_file(
                io.BytesIO(stego_bytes),
                as_attachment=True,
                download_name='stego_file.bin',
                mimetype='application/octet-stream'
            )

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Embed error: {e}")
        return jsonify({'error': f'Embedding failed: {str(e)}'}), 500


@app.route('/extract', methods=['POST'])
def extract():
    try:
        stego_file = request.files['stegoFile']
        password = request.form.get('password')
        file_type = request.form.get('fileType')

        if not password or not file_type:
            return jsonify({'error': 'All fields are required'}), 400

        stego_bytes = stego_file.read()

        if file_type == 'image':
            extracted_data = ImageSteganography.decode_lsb(stego_bytes)
        elif file_type == 'audio':
            extracted_data = AudioSteganography.decode_wav(stego_bytes)
        elif file_type == 'text':
            extracted_data = TextSteganography.decode_text(stego_bytes)
        else:
            marker = b'STEGO_V2'
            marker_pos = stego_bytes.rfind(marker)
            if marker_pos != -1:
                length_pos = marker_pos + len(marker)
                if length_pos + 4 <= len(stego_bytes):
                    payload_length = struct.unpack('>I', stego_bytes[length_pos:length_pos+4])[0]
                    payload_start = length_pos + 4
                    if payload_start + payload_length <= len(stego_bytes):
                        extracted_data = stego_bytes[payload_start:payload_start+payload_length]
                    else:
                        raise ValueError("Invalid payload length")
                else:
                    raise ValueError("Marker found but length field missing")
            else:
                raise ValueError("No steganographic data found in file")

        marker = b'STEGO_V2'
        marker_pos = extracted_data.find(marker)

        if marker_pos != -1:
            length_pos = marker_pos + len(marker)
            if length_pos + 4 <= len(extracted_data):
                payload_length = struct.unpack('>I', extracted_data[length_pos:length_pos+4])[0]
                encrypted_payload = extracted_data[length_pos+4:length_pos+4+payload_length]
            else:
                encrypted_payload = extracted_data[len(marker):]
        else:
            encrypted_payload = extracted_data

        try:
            payload_data = SecurityLayer.process_decode(encrypted_payload, password)
            return jsonify({'text': payload_data.decode('utf-8', errors='replace')})
        except Exception as e:
            print(f"Decryption error: {e}")
            return jsonify({'error': 'Invalid password or corrupted data'}), 401

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Extract error: {e}")
        return jsonify({'error': f'Extraction failed: {str(e)}'}), 500


# ===================== AUTHENTICATION ROUTES =====================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({'success': True, 'username': user.username})
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': 'Username already exists'})
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'success': False, 'message': 'Email already registered'})

    if len(data['password']) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters'})

    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    session['username'] = user.username
    return jsonify({'success': True, 'username': user.username})

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ===================== URL VERIFIER =====================

@app.route('/api/verify-url', methods=['POST'])
def verify_url():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        parsed = urlparse(url)
        domain = parsed.netloc

        if not domain:
            domain = url.split('/')[0]

        security_checks = []
        safety_score = 100
        warnings = []

        ssl_valid = False
        try:
            if url.startswith('https://'):
                context = ssl.create_default_context()
                with socket.create_connection((parsed.hostname, 443), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=parsed.hostname) as ssock:
                        cert = ssock.getpeercert()
                        ssl_valid = True
                        security_checks.append({'name': 'SSL Certificate', 'passed': True, 'message': 'Valid SSL certificate found'})
            else:
                security_checks.append({'name': 'SSL Certificate', 'passed': False, 'message': 'No HTTPS - Connection not encrypted'})
                safety_score -= 35
                warnings.append('Missing HTTPS encryption')
        except:
            security_checks.append({'name': 'SSL Certificate', 'passed': False, 'message': 'SSL validation failed'})
            safety_score -= 35
            warnings.append('Invalid or missing SSL certificate')

        try:
            domain_info = whois.whois(domain)
            creation_date = domain_info.creation_date
            if isinstance(creation_date, list):
                creation_date = creation_date[0]
            if creation_date:
                days_old = (datetime.now() - creation_date).days
                if days_old < 30:
                    safety_score -= 30
                    warnings.append(f'Very new domain ({days_old} days old)')
                    security_checks.append({'name': 'Domain Age', 'passed': False, 'message': f'Domain registered {days_old} days ago (VERY NEW)'})
                elif days_old < 90:
                    safety_score -= 15
                    warnings.append(f'New domain ({days_old} days old)')
                    security_checks.append({'name': 'Domain Age', 'passed': False, 'message': f'Domain registered {days_old} days ago (New)'})
                else:
                    security_checks.append({'name': 'Domain Age', 'passed': True, 'message': f'Domain registered {days_old} days ago'})
        except:
            security_checks.append({'name': 'Domain Age', 'passed': False, 'message': 'Could not verify domain age'})

        suspicious_patterns = ['free', 'bonus', 'win', 'prize', 'login', 'verify', 'secure', 'account', 'update', 'confirm']
        has_suspicious = any(pattern in url.lower() for pattern in suspicious_patterns)
        if has_suspicious:
            safety_score -= 20
            warnings.append('Contains suspicious keywords')
            security_checks.append({'name': 'Suspicious Keywords', 'passed': False, 'message': 'Contains phishing keywords'})
        else:
            security_checks.append({'name': 'Suspicious Keywords', 'passed': True, 'message': 'No suspicious keywords'})

        if re.match(r'\d+\.\d+\.\d+\.\d+', domain):
            safety_score -= 40
            warnings.append('URL contains IP address')
            security_checks.append({'name': 'IP Address', 'passed': False, 'message': 'Contains IP address (phishing indicator)'})
        else:
            security_checks.append({'name': 'IP Address', 'passed': True, 'message': 'Uses domain name'})

        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.top', '.xyz', '.club', '.online', '.site', '.space']
        tld = '.' + domain.split('.')[-1] if '.' in domain else ''
        if tld in suspicious_tlds:
            safety_score -= 25
            warnings.append(f'Suspicious TLD {tld}')
            security_checks.append({'name': 'Top-Level Domain', 'passed': False, 'message': f'Suspicious TLD {tld}'})
        else:
            security_checks.append({'name': 'Top-Level Domain', 'passed': True, 'message': f'Standard TLD'})

        safety_score = max(0, min(100, safety_score))

        if safety_score >= 80:
            status = "SAFE"
            color = "green"
            icon = "fa-shield-check"
            message = "This URL appears to be legitimate and secure."
            details = "All security checks passed."
        elif safety_score >= 60:
            status = "CAUTION"
            color = "yellow"
            icon = "fa-exclamation-triangle"
            message = "Exercise caution with this URL."
            details = "Some concerns detected."
        elif safety_score >= 40:
            status = "SUSPICIOUS"
            color = "orange"
            icon = "fa-skull"
            message = "This URL shows suspicious characteristics!"
            details = "Multiple red flags detected."
        else:
            status = "DANGEROUS"
            color = "red"
            icon = "fa-biohazard"
            message = "DANGER: This URL is highly suspicious!"
            details = "Do NOT visit this website!"

        return jsonify({
            'url': url, 'domain': domain, 'safety_score': safety_score,
            'status': status, 'color': color, 'icon': icon,
            'message': message, 'details': details, 'security_checks': security_checks,
            'warnings': warnings
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===================== PASSWORD STRENGTH CHECKER =====================

@app.route('/api/check-password', methods=['POST'])
def check_password():
    data = request.json
    password = data.get('password')

    if not password:
        return jsonify({'error': 'No password provided'}), 400

    score = 0
    feedback = []

    if len(password) >= 16:
        score += 30
        feedback.append("✓ Excellent length (16+ characters)")
    elif len(password) >= 12:
        score += 25
        feedback.append("✓ Good length (12+ characters)")
    elif len(password) >= 8:
        score += 15
        feedback.append("⚠️ Minimum length achieved")
    else:
        feedback.append("❌ Too short (minimum 8 characters)")

    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))

    variety_count = sum([has_upper, has_lower, has_digit, has_special])

    if variety_count == 4:
        score += 35
        feedback.append("✓ Excellent character variety")
    elif variety_count == 3:
        score += 25
        feedback.append("✓ Good character variety")
    elif variety_count == 2:
        score += 15
        feedback.append("⚠️ Limited character variety")
    else:
        score += 5
        feedback.append("❌ Very limited character variety")

    common_patterns = ['123456', 'password', 'qwerty', 'admin', 'letmein', 'welcome']
    if any(pattern in password.lower() for pattern in common_patterns):
        score -= 25
        feedback.append("❌ Contains common password pattern")

    score = max(0, min(100, score))

    if score >= 85:
        strength = "EXCELLENT"
        color = "emerald"
        message = "Outstanding! This password is extremely secure."
        time_to_crack = "centuries"
    elif score >= 70:
        strength = "STRONG"
        color = "green"
        message = "Strong password! Good protection."
        time_to_crack = "years"
    elif score >= 55:
        strength = "MODERATE"
        color = "yellow"
        message = "Moderate password. Consider adding more complexity."
        time_to_crack = "weeks"
    elif score >= 40:
        strength = "WEAK"
        color = "orange"
        message = "Weak password. Easily crackable."
        time_to_crack = "hours"
    else:
        strength = "VERY WEAK"
        color = "red"
        message = "Dangerously weak password!"
        time_to_crack = "seconds"

    return jsonify({
        'score': score, 'strength': strength, 'color': color,
        'message': message, 'time_to_crack': time_to_crack,
        'feedback': feedback, 'length': len(password), 'variety_count': variety_count
    })


# ===================== IP TRACKER =====================

@app.route('/api/track-ip', methods=['POST'])
def track_ip():
    data = request.json
    ip = data.get('ip')

    if not ip:
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            ip = response.json()['ip']
        except:
            return jsonify({'error': 'Could not detect IP'}), 500

    try:
        response = requests.get(f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,isp,org,timezone,query', timeout=5)
        data = response.json()

        if data.get('status') == 'fail':
            return jsonify({'error': 'Invalid IP address'}), 400

        return jsonify({
            'ip': ip, 'city': data.get('city', 'N/A'), 'region': data.get('regionName', 'N/A'),
            'country': data.get('country', 'N/A'), 'latitude': data.get('lat'), 'longitude': data.get('lon'),
            'isp': data.get('isp', 'N/A'), 'organization': data.get('org', 'N/A'), 'timezone': data.get('timezone', 'N/A')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===================== EMAIL ANALYZER =====================

@app.route('/api/analyze-email', methods=['POST'])
def analyze_email():
    data = request.json
    email_content = data.get('email')

    if not email_content:
        return jsonify({'error': 'No email content provided'}), 400

    risk_score = 0
    threat_indicators = []

    urgent_patterns = [r'\b(urgent|immediately|asap|action required)\b', r'\b(verify|confirm|account suspended)\b']
    for pattern in urgent_patterns:
        if re.search(pattern, email_content.lower()):
            risk_score += 15
            threat_indicators.append({'type': 'Urgency Manipulation', 'severity': 'HIGH', 'description': 'Contains urgent language'})
            break

    links = re.findall(r'https?://[^\s<>"]+', email_content)
    suspicious_links = [l for l in links if not any(trusted in l.lower() for trusted in ['google.com', 'microsoft.com', 'apple.com'])]
    if suspicious_links:
        risk_score += min(len(suspicious_links) * 10, 30)
        threat_indicators.append({'type': 'Suspicious Links', 'severity': 'HIGH', 'description': f'{len(suspicious_links)} suspicious link(s)'})

    credential_patterns = [r'\b(password|login|verify account)\b', r'\b(banking|credit card|payment)\b']
    for pattern in credential_patterns:
        if re.search(pattern, email_content.lower()):
            risk_score += 20
            threat_indicators.append({'type': 'Credential Harvesting', 'severity': 'CRITICAL', 'description': 'Requests sensitive information'})
            break

    risk_score = min(risk_score, 100)

    if risk_score >= 70:
        status = "DANGEROUS - PHISHING"
        color = "red"
        threat_level = "CRITICAL"
        message = "This email shows strong indicators of a phishing attack!"
        action = "DO NOT click any links or download attachments."
    elif risk_score >= 50:
        status = "SUSPICIOUS - HIGH RISK"
        color = "orange"
        threat_level = "HIGH"
        message = "This email has multiple characteristics of phishing."
        action = "Exercise extreme caution."
    elif risk_score >= 30:
        status = "CAUTION - MEDIUM RISK"
        color = "yellow"
        threat_level = "MEDIUM"
        message = "This email shows some suspicious elements."
        action = "Verify the email's legitimacy."
    else:
        status = "LIKELY SAFE"
        color = "green"
        threat_level = "LOW"
        message = "No obvious phishing indicators detected."
        action = "Still practice caution with unexpected emails."

    return jsonify({
        'status': status, 'color': color, 'threat_level': threat_level,
        'risk_score': risk_score, 'message': message, 'action': action,
        'threat_indicators': threat_indicators, 'suspicious_links': suspicious_links[:3]
    })


## ===================== ANTI-PHISHING CHECKER =====================

@app.route('/api/check-phishing', methods=['POST'])
def check_phishing():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]

        if not domain:
            return jsonify({'error': 'Invalid URL — could not extract domain. Please enter a valid URL like https://example.com'}), 400

        # Strip port number for clean domain checks
        domain_clean = domain.split(':')[0].lower()

        phishing_score = 0
        risk_factors = []

        # Check 1: IP address used instead of domain name
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', domain_clean):
            phishing_score += 35
            risk_factors.append({
                'type': 'IP Address Used',
                'risk': 'HIGH',
                'description': f'URL uses raw IP address: {domain_clean}',
                'impact': 'Legitimate sites use domain names, not IP addresses'
            })

        # Check 2: Suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.top', '.xyz', '.club', '.online', '.site', '.space', '.buzz']
        matched_tld = next((tld for tld in suspicious_tlds if domain_clean.endswith(tld)), None)
        if matched_tld:
            phishing_score += 25
            risk_factors.append({
                'type': 'Suspicious TLD',
                'risk': 'MEDIUM',
                'description': f'Domain uses suspicious TLD: {matched_tld}',
                'impact': 'These TLDs are frequently abused by phishing campaigns'
            })

        # Check 3: Excessive subdomains (more than 3 dots = 4+ parts)
        subdomain_count = domain_clean.count('.')
        if subdomain_count > 3:
            phishing_score += 20
            risk_factors.append({
                'type': 'Excessive Subdomains',
                'risk': 'MEDIUM',
                'description': f'Domain has {subdomain_count} dots ({subdomain_count + 1} parts): {domain_clean}',
                'impact': 'Attackers nest real brand names in subdomains to deceive users'
            })

        # Check 4: Abnormally long URL
        if len(url) > 100:
            phishing_score += 15
            risk_factors.append({
                'type': 'Long URL',
                'risk': 'LOW',
                'description': f'URL is {len(url)} characters long',
                'impact': 'Excessively long URLs are used to hide malicious destinations'
            })

        # Check 5: @ symbol in URL
        if '@' in parsed.netloc or '@' in parsed.path:
            phishing_score += 30
            risk_factors.append({
                'type': '@ Symbol in URL',
                'risk': 'HIGH',
                'description': 'URL contains an @ symbol',
                'impact': 'Browsers ignore everything before @ — used to disguise true destination'
            })

        # Check 6: Brand impersonation in domain (not path)
        real_brand_domains = {
            'paypal': 'paypal.com',
            'amazon': 'amazon.com',
            'google': 'google.com',
            'microsoft': 'microsoft.com',
            'apple': 'apple.com',
            'facebook': 'facebook.com',
            'instagram': 'instagram.com',
            'netflix': 'netflix.com',
            'bank': None  # generic keyword, always flag
        }
        flagged_brands = []
        for brand, real_domain in real_brand_domains.items():
            if brand in domain_clean.lower():
                # Skip if this IS the actual brand domain
                if real_domain and (domain_clean.lower() == real_domain or domain_clean.lower().endswith('.' + real_domain)):
                    continue
                flagged_brands.append(brand)

        if flagged_brands:
            phishing_score += 25
            risk_factors.append({
                'type': 'Brand Impersonation',
                'risk': 'HIGH',
                'description': f'Domain contains brand keyword(s): {", ".join(flagged_brands[:3])}',
                'impact': 'Designed to trick users into thinking it is a trusted brand site'
            })

        # Check 7: Hyphen abuse in domain (e.g. paypal-secure-login.com)
        hyphen_count = domain_clean.count('-')
        if hyphen_count >= 2:
            score_increment = 35 if hyphen_count >= 3 else 20
            phishing_score += score_increment
            risk_factors.append({
                'type': 'Hyphen Abuse',
                'risk': 'MEDIUM' if hyphen_count >= 3 else 'LOW',
                'description': f'Domain contains {hyphen_count} hyphens: {domain_clean}',
                'impact': 'Multiple hyphens are a common phishing domain pattern used to mimic long descriptive URLs'
            })

        # Check 8: Tunnel / Free Hosting Providers
        tunnel_providers = [
            'trycloudflare.com', 'ngrok.io', 'vercel.app', 'github.io', 
            'surge.sh', 'localtonet.com', 'web.app', 'firebaseapp.com',
            '000webhostapp.com', 'render.com', 'netlify.app'
        ]
        is_tunnel = any(domain_clean.endswith(provider) for provider in tunnel_providers)
        if is_tunnel:
            # Only flag if it's a subdomain (e.g. something.trycloudflare.com)
            provider_matched = next(p for p in tunnel_providers if domain_clean.endswith(p))
            if domain_clean != provider_matched:
                phishing_score += 25
                risk_factors.append({
                    'type': 'Tunnel Service Usage',
                    'risk': 'MEDIUM',
                    'description': f'Site is hosted on a tunnel/free provider: {provider_matched}',
                    'impact': 'Phishers frequently use these services to host temporary malicious sites'
                })

        # Check 9: Suspicious keywords in the full URL
        phishing_keywords = [
            'login', 'signin', 'verify', 'secure', 'account', 'update',
            'confirm', 'banking', 'password', 'credential', 'webscr', 
            'ebayisapi', 'auth', 'portal', 'validate', 'session', 'redirect',
            'billing', 'support', 'office365', 'outlook', 'proton', 'drive',
            'surge', 'cloud', 'tunnel', 'hosting'
        ]
        matched_keywords = [kw for kw in phishing_keywords if kw in url.lower()]
        if matched_keywords:
            phishing_score += min(len(matched_keywords) * 10, 30)
            risk_factors.append({
                'type': 'Phishing Keywords',
                'risk': 'MEDIUM',
                'description': f'URL contains suspicious keywords: {", ".join(matched_keywords[:4])}',
                'impact': 'Commonly used to mimic login or verification pages'
            })

        phishing_score = max(0, min(phishing_score, 100))

        if phishing_score >= 70:
            status = "PHISHING SITE"
            color = "red"
            icon = "fa-biohazard"
            risk_level = "CRITICAL"
            message = "DANGER: This website shows strong indicators of a phishing attack!"
            recommendation = "Do NOT enter any personal information. Close this page immediately."
        elif phishing_score >= 50:
            status = "SUSPICIOUS"
            color = "orange"
            icon = "fa-exclamation-triangle"
            risk_level = "HIGH"
            message = "This website has multiple phishing indicators."
            recommendation = "Exercise extreme caution. Verify via official channels before proceeding."
        elif phishing_score >= 30:
            status = "CAUTION"
            color = "yellow"
            icon = "fa-shield-exclamation"
            risk_level = "MEDIUM"
            message = "Some suspicious elements were detected."
            recommendation = "Double-check the domain carefully before entering any information."
        else:
            status = "LIKELY SAFE"
            color = "green"
            icon = "fa-shield-check"
            risk_level = "LOW"
            message = "No obvious phishing indicators detected."
            recommendation = "Still practise safe browsing — verify you typed the URL correctly."

        return jsonify({
            'url': url,
            'domain': domain_clean,
            'status': status,
            'color': color,
            'icon': icon,
            'risk_level': risk_level,
            'phishing_score': phishing_score,
            'message': message,
            'recommendation': recommendation,
            'risk_factors': risk_factors
        })

    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500
        

# ===================== SAFETY TIPS =====================

@app.route('/api/safety-tips')
def safety_tips():
    tips = {
        'categories': [
            {
                'title': '🔐 Account Security', 'icon': 'fa-lock', 'color': 'cyan',
                'tips': [
                    {'title': 'Enable 2FA Everywhere', 'description': 'Two-Factor Authentication adds an extra layer of security.', 'priority': 'Critical'},
                    {'title': 'Use Password Manager', 'description': 'Never reuse passwords. Use a trusted password manager.', 'priority': 'High'},
                    {'title': 'Regular Password Changes', 'description': 'Change passwords every 60-90 days.', 'priority': 'Medium'},
                    {'title': 'Check Device Pairing', 'description': 'Regularly review paired devices in messaging apps.', 'priority': 'High'}
                ]
            },
            {
                'title': '📱 Mobile Device Security', 'icon': 'fa-mobile-alt', 'color': 'purple',
                'tips': [
                    {'title': 'Call Forwarding Check', 'description': 'Dial *#61# to check call forwarding. Use ##002# to disable.', 'priority': 'High'},
                    {'title': 'Play Protect Scan', 'description': 'Run Google Play Protect daily to scan for malicious apps.', 'priority': 'Critical'},
                    {'title': 'Unknown Sources', 'description': 'NEVER install apps from unknown sources.', 'priority': 'Critical'},
                    {'title': 'App Permissions', 'description': 'Regularly review and revoke unnecessary app permissions.', 'priority': 'High'}
                ]
            },
            {
                'title': '🌐 Browser & Online Security', 'icon': 'fa-globe', 'color': 'blue',
                'tips': [
                    {'title': 'Remove Third-Party Connections', 'description': 'Go to browser settings → Privacy → Third-party services.', 'priority': 'Medium'},
                    {'title': 'Use HTTPS Everywhere', 'description': 'Install browser extension "HTTPS Everywhere".', 'priority': 'High'},
                    {'title': 'Clear Browser Data', 'description': 'Regularly clear cache, cookies, and browsing history.', 'priority': 'Medium'},
                    {'title': 'Disable Password Saving', 'description': 'NEVER save passwords in browsers.', 'priority': 'Critical'}
                ]
            },
            {
                'title': '🛡️ Advanced Protection', 'icon': 'fa-shield-virus', 'color': 'red',
                'tips': [
                    {'title': 'RAT Detection', 'description': 'If you suspect Remote Access Trojan: Disconnect internet, backup data, factory reset.', 'priority': 'Critical'},
                    {'title': 'Security Scans', 'description': 'Run manufacturer security scans weekly.', 'priority': 'High'},
                    {'title': 'Monitor Bank Statements', 'description': 'Check bank statements weekly for unauthorized transactions.', 'priority': 'Critical'},
                    {'title': 'Social Engineering', 'description': 'Never share OTPs or passwords with anyone.', 'priority': 'Critical'}
                ]
            },
            {
                'title': '📧 Email & Phishing Protection', 'icon': 'fa-envelope', 'color': 'yellow',
                'tips': [
                    {'title': 'Verify Sender Address', 'description': 'Check actual email address, not just display name.', 'priority': 'Critical'},
                    {'title': 'Hover Before Clicking', 'description': 'Hover over links to see actual destination.', 'priority': 'High'},
                    {'title': 'Check for Urgency', 'description': 'Phishing emails often create urgency.', 'priority': 'High'},
                    {'title': 'Report Phishing', 'description': 'Forward suspicious emails to report@phishing.gov.in', 'priority': 'Medium'}
                ]
            }
        ]
    }
    return jsonify(tips)


# ===================== CYBER LAWS =====================

@app.route('/api/cyber-laws')
def cyber_laws():
    return jsonify({
        'categories': [
            {
                'name': '🇮🇳 Indian Cyber Laws',
                'icon': 'fa-gavel',
                'laws': [
                    {'section': 'Section 43', 'title': 'Penalty for Damage to Computer Systems', 'description': 'Unauthorized access or damage to computer systems.', 'punishment': 'Compensation up to ₹1 Crore', 'severity': 'Medium'},
                    {'section': 'Section 66', 'title': 'Computer Related Offenses', 'description': 'Hacking, identity theft, unauthorized access.', 'punishment': '3 years imprisonment + ₹5,00,000 fine', 'severity': 'High'},
                    {'section': 'Section 66C', 'title': 'Identity Theft', 'description': 'Fraudulent use of electronic signature or password.', 'punishment': '3 years imprisonment + ₹1,00,000 fine', 'severity': 'High'},
                    {'section': 'Section 66D', 'title': 'Cheating by Personation', 'description': 'Cheating using computer resources.', 'punishment': '3 years imprisonment + ₹1,00,000 fine', 'severity': 'High'},
                    {'section': 'Section 66E', 'title': 'Violation of Privacy', 'description': 'Capturing or transmitting private images without consent.', 'punishment': '3 years imprisonment or ₹2,00,000 fine', 'severity': 'High'},
                    {'section': 'Section 66F', 'title': 'Cyber Terrorism', 'description': 'Acts threatening unity and security of India.', 'punishment': 'Life imprisonment', 'severity': 'Critical'},
                    {'section': 'Section 67', 'title': 'Publishing Obscene Material', 'description': 'Publishing obscene material in electronic form.', 'punishment': '3 years imprisonment + ₹5,00,000 fine', 'severity': 'High'},
                    {'section': 'Section 67A', 'title': 'Child Pornography', 'description': 'Publishing child pornography.', 'punishment': '7 years imprisonment + ₹10,00,000 fine', 'severity': 'Critical'},
                    {'section': 'Section 72', 'title': 'Breach of Confidentiality', 'description': 'Disclosing information without consent.', 'punishment': '2 years imprisonment + ₹1,00,000 fine', 'severity': 'Medium'}
                ]
            },
            {
                'name': '💻 International Cyber Laws',
                'icon': 'fa-globe',
                'laws': [
                    {'section': 'GDPR (EU)', 'title': 'General Data Protection Regulation', 'description': 'Protects personal data of EU citizens.', 'punishment': 'Fines up to €20 million or 4% of global turnover', 'severity': 'Critical'},
                    {'section': 'CFAA (USA)', 'title': 'Computer Fraud and Abuse Act', 'description': 'Prohibits unauthorized computer access.', 'punishment': 'Imprisonment up to 20 years', 'severity': 'Critical'},
                    {'section': 'DMCA (USA)', 'title': 'Digital Millennium Copyright Act', 'description': 'Protects copyrighted digital content.', 'punishment': 'Fines up to $150,000 per work', 'severity': 'High'},
                    {'section': 'ECPA (USA)', 'title': 'Electronic Communications Privacy Act', 'description': 'Protects wire and electronic communications.', 'punishment': 'Imprisonment up to 5 years', 'severity': 'High'}
                ]
            },
            {
                'name': '🔐 Data Protection Laws',
                'icon': 'fa-shield-hooded',
                'laws': [
                    {'section': 'DPDP Act 2023', 'title': 'Digital Personal Data Protection Act', 'description': "India's new data protection law.", 'punishment': 'Fines up to ₹250 Crores', 'severity': 'Critical'},
                    {'section': 'CCPA', 'title': 'California Consumer Privacy Act', 'description': 'Gives consumers control over personal information.', 'punishment': 'Fines up to $7,500 per violation', 'severity': 'High'}
                ]
            }
        ]
    })


# ===================== COMPLAINT PORTALS =====================

@app.route('/api/complaint-portals')
def complaint_portals():
    portals = {
        'indian_portals': [
            {'name': 'National Cyber Crime Portal', 'url': 'https://cybercrime.gov.in', 'description': 'Official portal for reporting cyber crimes', 'type': 'Cyber Crime', 'hotline': '1930', 'icon': 'fa-police'},
            {'name': 'Sanchar Saathi', 'url': 'https://sancharsaathi.gov.in', 'description': 'Report mobile connection fraud', 'type': 'Telecom Fraud', 'hotline': '1963', 'icon': 'fa-mobile-alt'},
            {'name': 'RBI Ombudsman', 'url': 'https://cms.rbi.org.in', 'description': 'Report banking frauds', 'type': 'Financial Fraud', 'hotline': '14440', 'icon': 'fa-university'},
            {'name': 'SEBI SCORES', 'url': 'https://scores.gov.in', 'description': 'Report investment scams', 'type': 'Investment Fraud', 'icon': 'fa-chart-line'},
            {'name': 'NPCI Helpline', 'url': 'https://www.npci.org.in', 'description': 'Report UPI frauds', 'type': 'Digital Payment', 'hotline': '1800-120-1740', 'icon': 'fa-credit-card'},
            {'name': 'Child Helpline', 'url': 'https://www.childlineindia.org', 'description': 'Report child exploitation', 'type': 'Child Protection', 'hotline': '1098', 'icon': 'fa-child'}
        ],
        'international_portals': [
            {'name': 'IC3 - FBI', 'url': 'https://www.ic3.gov', 'description': 'Internet Crime Complaint Center', 'type': 'International', 'icon': 'fa-globe'},
            {'name': 'Europol', 'url': 'https://www.europol.europa.eu/report-a-crime', 'description': 'Report cyber crimes in EU', 'type': 'International', 'icon': 'fa-euro-sign'}
        ]
    }
    return jsonify(portals)


# ===================== STUDENT TOOLS APIs =====================

# Roadmap Data - 15 Cybersecurity Roles
@app.route('/api/roadmap-data')
def roadmap_data():
    roles = [
        {'title': 'Security Analyst', 'qualifications': "Bachelor's in CS/IT, Security+ certification", 'basic': 'Network protocols, OS fundamentals, SIEM tools, Log analysis', 'intermediate': 'Threat hunting, Incident response, Python scripting', 'advanced': 'Security architecture, Malware analysis, Cloud security', 'salary': '₹5-12 LPA', 'description': 'Monitor and protect organization assets from cyber threats'},
        {'title': 'Penetration Tester', 'qualifications': "Bachelor's degree, CEH/OSCP certification", 'basic': 'Networking, Linux, Web technologies, Basic scripting', 'intermediate': 'Exploitation techniques, Metasploit, Burp Suite, SQL injection', 'advanced': 'Advanced exploitation, Reverse engineering, Red teaming', 'salary': '₹6-15 LPA', 'description': 'Find vulnerabilities through authorized simulated attacks'},
        {'title': 'Security Engineer', 'qualifications': "Bachelor's in CS/IT, CISSP/CCSP", 'basic': 'System administration, Firewalls, IDS/IPS, Network security', 'intermediate': 'Cloud security, DevSecOps, Security automation', 'advanced': 'Security architecture, SIEM deployment, IAM', 'salary': '₹8-20 LPA', 'description': 'Build and maintain security infrastructure'},
        {'title': 'SOC Analyst', 'qualifications': "Bachelor's degree, Security+ or CySA+", 'basic': 'Log analysis, Security monitoring, Alert triage, SIEM tools', 'intermediate': 'Threat hunting, Incident investigation, SOAR', 'advanced': 'Malware analysis, Threat intelligence, SOC management', 'salary': '₹4-10 LPA', 'description': 'Monitor security alerts and respond to incidents'},
        {'title': 'Incident Responder', 'qualifications': "Bachelor's degree, GCIH certification", 'basic': 'Incident handling, Forensics basics, EDR tools', 'intermediate': 'Digital forensics, Malware analysis, Containment strategies', 'advanced': 'Advanced forensics, Threat hunting, IR planning', 'salary': '₹6-18 LPA', 'description': 'Respond to and investigate security incidents'},
        {'title': 'Forensic Investigator', 'qualifications': "Bachelor's degree, GCFE/GCFA certification", 'basic': 'Disk imaging, File system analysis, Log analysis', 'intermediate': 'Memory forensics, Network forensics, Mobile forensics', 'advanced': 'Advanced malware forensics, Expert testimony', 'salary': '₹7-16 LPA', 'description': 'Investigate digital evidence after security incidents'},
        {'title': 'Security Architect', 'qualifications': "Master's preferred, CISSP/CISM certification", 'basic': 'Security frameworks, Network architecture, Risk assessment', 'intermediate': 'Cloud security, Zero trust, Security design patterns', 'advanced': 'Enterprise security strategy, Risk management', 'salary': '₹15-30 LPA', 'description': 'Design comprehensive security systems'},
        {'title': 'GRC Analyst', 'qualifications': "Bachelor's degree, CRISC/CISA certification", 'basic': 'Compliance frameworks, Risk assessment, Audit basics', 'intermediate': 'Policy development, Audit management, Risk analysis', 'advanced': 'Enterprise risk management, Compliance strategy', 'salary': '₹5-12 LPA', 'description': 'Ensure compliance with security regulations'},
        {'title': 'Cloud Security Engineer', 'qualifications': "Bachelor's degree, AWS/Azure security certs", 'basic': 'Cloud platforms (AWS/Azure/GCP), IAM basics', 'intermediate': 'Cloud security tools, Infrastructure as code', 'advanced': 'Cloud architecture, DevSecOps, Multi-cloud security', 'salary': '₹8-22 LPA', 'description': 'Secure cloud infrastructure and applications'},
        {'title': 'Application Security Engineer', 'qualifications': "Bachelor's in CS, CSSLP", 'basic': 'Programming, Web technologies, OWASP Top 10', 'intermediate': 'SAST/DAST tools, Code review, Secure coding', 'advanced': 'DevSecOps, Security automation, Threat modeling', 'salary': '₹7-18 LPA', 'description': 'Secure software development lifecycle'},
        {'title': 'Network Security Engineer', 'qualifications': "Bachelor's degree, CCNA/CCNP Security", 'basic': 'Routing/switching, Firewalls, VPNs', 'intermediate': 'Network monitoring, IDS/IPS, NAC', 'advanced': 'Network architecture, DDoS mitigation', 'salary': '₹6-15 LPA', 'description': 'Protect network infrastructure'},
        {'title': 'Malware Analyst', 'qualifications': "Bachelor's degree, GREM certification", 'basic': 'Assembly basics, Debugging tools', 'intermediate': 'Static/dynamic analysis, Sandboxing', 'advanced': 'Advanced reverse engineering, Exploit analysis', 'salary': '₹7-16 LPA', 'description': 'Analyze malicious software'},
        {'title': 'Threat Intelligence Analyst', 'qualifications': "Bachelor's degree", 'basic': 'OSINT, Threat feeds, IoCs', 'intermediate': 'Threat modeling, Intelligence platforms', 'advanced': 'Advanced threat hunting, Intelligence reporting', 'salary': '₹6-14 LPA', 'description': 'Gather and analyze threat intelligence'},
        {'title': 'Security Auditor', 'qualifications': "Bachelor's degree, CISA/CISSP", 'basic': 'Audit frameworks, Control assessment', 'intermediate': 'Audit planning, Evidence collection', 'advanced': 'Risk-based auditing, Compliance reporting', 'salary': '₹5-12 LPA', 'description': 'Assess security controls and compliance'},
        {'title': 'CISO', 'qualifications': "Master's degree, CISSP/CISM, 10+ years experience", 'basic': 'Security strategy, Risk management', 'intermediate': 'Budget management, Team leadership', 'advanced': 'Executive communication, Board reporting', 'salary': '₹25-60 LPA', 'description': 'Lead organization security strategy'}
    ]
    return jsonify(roles)

# Study Resources
@app.route('/api/resources-data')
def resources_data():
    return jsonify([
        {'title': '📘 Handbook of Cybersecurity', 'url': 'https://cyber.gov.gr/wp-content/uploads/2025/03/Cybersecurity-Handbook-English-version-compressed.pdf', 'type': 'PDF', 'size': '2.5 MB'},
        {'title': '📗 Introduction to Cybersecurity', 'url': 'https://uou.ac.in/sites/default/files/slm/Introduction-cyber-security.pdf', 'type': 'PDF', 'size': '3.1 MB'},
        {'title': '📕 Advanced Cybersecurity Techniques', 'url': 'https://uou.ac.in/sites/default/files/slm/MIT(CS)-203.pdf', 'type': 'PDF', 'size': '4.2 MB'},
        {'title': '🔐 Cryptography', 'url': 'https://toc.cryptobook.us/book.pdf', 'type': 'PDF', 'size': '8.5 MB'},
        {'title': '🌐 Network Security', 'url': 'https://edu.anarcho-copy.org/TCP%20IP%20-%20Network/Network%20Security.pdf', 'type': 'PDF', 'size': '5.3 MB'},
        {'title': '💻 Ethical Hacking', 'url': 'https://technicsdotblog.wordpress.com/wp-content/uploads/2018/01/9781482231618.pdf', 'type': 'PDF', 'size': '12.1 MB'},
        {'title': '🛡️ Web Application Security', 'url': 'https://owasp.org/www-project-web-security-testing-guide/', 'type': 'Guide', 'size': 'Online'},
        {'title': '📱 Mobile Security Guide', 'url': 'https://mobile-security.gitbook.io/mobile-security-testing-guide/', 'type': 'Guide', 'size': 'Online'}
    ])

# Course Suggestions
@app.route('/api/courses-data')
def courses_data():
    return jsonify([
        {'title': 'NPTEL - Introduction to Cybersecurity', 'level': 'Beginner', 'url': 'https://nptel.ac.in/courses/106105215', 'platform': 'NPTEL', 'certification': 'Free Certificate', 'duration': '8 weeks'},
        {'title': 'Infosys Springboard - Cybersecurity Fundamentals', 'level': 'Beginner', 'url': 'https://infyspringboard.onwingspan.com', 'platform': 'Infosys', 'certification': 'Free', 'duration': '4 weeks'},
        {'title': 'GeeksforGeeks - Cyber Security Tutorial', 'level': 'Beginner', 'url': 'https://www.geeksforgeeks.org/cyber-security-tutorial/', 'platform': 'GeeksforGeeks', 'certification': 'Free', 'duration': 'Self-paced'},
        {'title': 'NPTEL - Information Security', 'level': 'Intermediate', 'url': 'https://nptel.ac.in/courses/106106129', 'platform': 'NPTEL', 'certification': 'Free Certificate', 'duration': '12 weeks'},
        {'title': 'Infosys Springboard - Ethical Hacking', 'level': 'Intermediate', 'url': 'https://infyspringboard.onwingspan.com', 'platform': 'Infosys', 'certification': 'Free', 'duration': '6 weeks'},
        {'title': 'Coursera - IBM Cybersecurity Analyst', 'level': 'Intermediate', 'url': 'https://www.coursera.org/professional-certificates/ibm-cybersecurity-analyst', 'platform': 'Coursera', 'certification': 'Paid Certificate', 'duration': '8 months'},
        {'title': 'NPTEL - Cyber Security and Privacy', 'level': 'Advanced', 'url': 'https://nptel.ac.in/courses/106105214', 'platform': 'NPTEL', 'certification': 'Free Certificate', 'duration': '12 weeks'},
        {'title': 'GeeksforGeeks - Advanced Penetration Testing', 'level': 'Advanced', 'url': 'https://www.geeksforgeeks.org/penetration-testing/', 'platform': 'GeeksforGeeks', 'certification': 'Free', 'duration': 'Self-paced'},
        {'title': 'SANS - SEC504: Hacker Tools', 'level': 'Advanced', 'url': 'https://www.sans.org/cyber-security-courses/hacker-tools-techniques/', 'platform': 'SANS', 'certification': 'Paid', 'duration': '6 days'},
        {'title': 'TryHackMe - Pre Security Path', 'level': 'Beginner', 'url': 'https://tryhackme.com/path/outline/presecurity', 'platform': 'TryHackMe', 'certification': 'Free', 'duration': 'Self-paced'}
    ])

# Quiz Questions (20 Questions)
@app.route('/api/quiz-questions')
def quiz_questions():
    questions = [
        {'id': 1, 'question': 'What does DDoS stand for?', 'options': ['Distributed Denial of Service', 'Direct Data Output System', 'Dynamic Domain Operating System', 'Digital Defense Online Service'], 'correct': 0},
        {'id': 2, 'question': 'What is phishing?', 'options': ['Fishing for compliments', 'Fraudulent attempt to obtain sensitive information', 'A type of malware', 'Network security protocol'], 'correct': 1},
        {'id': 3, 'question': 'What is the purpose of a firewall?', 'options': ['To protect against viruses', 'To monitor and control network traffic', 'To encrypt data', 'To backup files'], 'correct': 1},
        {'id': 4, 'question': 'What is 2FA?', 'options': ['Two File Access', 'Two-Factor Authentication', 'Technical File Analysis', 'Trusted Firewall Access'], 'correct': 1},
        {'id': 5, 'question': 'What is ransomware?', 'options': ['Software that steals passwords', 'Malware that encrypts data and demands payment', 'Antivirus program', 'Network monitoring tool'], 'correct': 1},
        {'id': 6, 'question': 'What is social engineering?', 'options': ['Engineering social media', 'Psychological manipulation to get information', 'Building social networks', 'Software development'], 'correct': 1},
        {'id': 7, 'question': 'What does VPN stand for?', 'options': ['Virtual Private Network', 'Very Protected Network', 'Virtual Public Network', 'Verified Private Network'], 'correct': 0},
        {'id': 8, 'question': 'Which is the strongest password?', 'options': ['password123', 'admin2024', 'P@ssw0rd!23#', 'qwerty'], 'correct': 2},
        {'id': 9, 'question': 'What is SQL injection?', 'options': ['Database backup method', 'Code injection technique to attack databases', 'SQL query optimization', 'Database encryption'], 'correct': 1},
        {'id': 10, 'question': 'What is HTTPS?', 'options': ['HyperText Transfer Protocol Secure', 'High Transfer Protocol System', 'HyperText Transfer Protocol Simple', 'High Tech Protocol Standard'], 'correct': 0},
        {'id': 11, 'question': 'What is a zero-day vulnerability?', 'options': ['Vulnerability fixed after 30 days', 'Unknown vulnerability with no patch', 'Day zero of testing', 'Vulnerability in software update'], 'correct': 1},
        {'id': 12, 'question': 'What is the purpose of encryption?', 'options': ['To compress data', 'To hide data from unauthorized access', 'To backup data', 'To speed up data transfer'], 'correct': 1},
        {'id': 13, 'question': 'What is a botnet?', 'options': ['Robot network', 'Network of compromised computers', 'Anti-virus network', 'Cloud computing network'], 'correct': 1},
        {'id': 14, 'question': 'What does SIEM stand for?', 'options': ['Security Information and Event Management', 'System Information Enterprise Manager', 'Security Intelligence Enterprise Module', 'System Integration Event Management'], 'correct': 0},
        {'id': 15, 'question': 'What is the best practice for password security?', 'options': ['Use same password everywhere', 'Write passwords on sticky notes', 'Use unique, complex passwords with manager', 'Use simple easy-to-remember passwords'], 'correct': 2},
        {'id': 16, 'question': 'What is malware?', 'options': ['Software that malfunctions', 'Malicious software designed to damage systems', 'Hardware security device', 'Network protocol'], 'correct': 1},
        {'id': 17, 'question': 'What is a rootkit?', 'options': ['Root directory tool', 'Malware that hides its presence', 'Security scanner', 'Network diagnostic tool'], 'correct': 1},
        {'id': 18, 'question': 'What is the CIA triad?', 'options': ['Central Intelligence Agency', 'Confidentiality, Integrity, Availability', 'Computer Internet Access', 'Cyber Intelligence Analysis'], 'correct': 1},
        {'id': 19, 'question': 'What is XSS?', 'options': ['XML Style Sheet', 'Cross-Site Scripting', 'Extra Security System', 'X-ray Security Scan'], 'correct': 1},
        {'id': 20, 'question': 'What is the purpose of penetration testing?', 'options': ['To break into systems illegally', 'To identify vulnerabilities through authorized attacks', 'To install antivirus', 'To backup data'], 'correct': 1}
    ]
    return jsonify(questions)

# Save Quiz Result
@app.route('/api/save-quiz-result', methods=['POST'])
def save_quiz_result():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    result = QuizResult(
        user_id=session['user_id'],
        score=data.get('score', 0),
        total=data.get('total', 20)
    )
    db.session.add(result)
    db.session.commit()
    return jsonify({'success': True})

# Glossary Data (50+ Terms)
@app.route('/api/glossary-data')
def glossary_data():
    terms = [
        {'term': 'Phishing', 'meaning': 'Fraudulent attempt to obtain sensitive information by disguising as trustworthy entity'},
        {'term': 'Malware', 'meaning': 'Malicious software designed to damage or disrupt systems'},
        {'term': 'Firewall', 'meaning': 'Network security system that monitors and controls incoming/outgoing traffic'},
        {'term': 'Encryption', 'meaning': 'Process of converting information into code to prevent unauthorized access'},
        {'term': 'VPN', 'meaning': 'Virtual Private Network - creates secure connection over internet'},
        {'term': 'DDoS', 'meaning': 'Distributed Denial of Service - overwhelms system with traffic'},
        {'term': 'Ransomware', 'meaning': 'Malware that encrypts data and demands payment for decryption'},
        {'term': 'Social Engineering', 'meaning': 'Psychological manipulation to trick people into revealing information'},
        {'term': 'Zero-day', 'meaning': 'Previously unknown vulnerability with no available patch'},
        {'term': 'Botnet', 'meaning': 'Network of compromised computers controlled by attacker'},
        {'term': 'SQL Injection', 'meaning': 'Code injection technique to attack databases'},
        {'term': 'XSS', 'meaning': 'Cross-Site Scripting - injection of malicious scripts into websites'},
        {'term': '2FA', 'meaning': 'Two-Factor Authentication - requires two forms of verification'},
        {'term': 'Penetration Testing', 'meaning': 'Authorized simulated attack to identify vulnerabilities'},
        {'term': 'SIEM', 'meaning': 'Security Information and Event Management - security monitoring system'},
        {'term': 'IDS', 'meaning': 'Intrusion Detection System - monitors for malicious activity'},
        {'term': 'IPS', 'meaning': 'Intrusion Prevention System - blocks detected threats'},
        {'term': 'SSL/TLS', 'meaning': 'Secure Sockets Layer/Transport Layer Security - encrypts internet connections'},
        {'term': 'Rootkit', 'meaning': 'Software that hides malicious activity by gaining root-level access'},
        {'term': 'Keylogger', 'meaning': 'Software that records keystrokes to steal information'},
        {'term': 'Spyware', 'meaning': 'Software that secretly gathers user information'},
        {'term': 'Adware', 'meaning': 'Software that automatically displays unwanted advertisements'},
        {'term': 'Trojan', 'meaning': 'Malware disguised as legitimate software'},
        {'term': 'Worm', 'meaning': 'Self-replicating malware that spreads across networks'},
        {'term': 'Virus', 'meaning': 'Malware that spreads by attaching to other programs'},
        {'term': 'Honeypot', 'meaning': 'Decoy system designed to attract and trap attackers'},
        {'term': 'Backdoor', 'meaning': 'Hidden method to bypass normal authentication'},
        {'term': 'Brute Force', 'meaning': 'Attack that tries all possible password combinations'},
        {'term': 'Man-in-the-Middle', 'meaning': 'Attack where attacker intercepts communication'},
        {'term': 'Packet Sniffing', 'meaning': 'Capturing and analyzing network traffic'},
        {'term': 'Spoofing', 'meaning': 'Falsifying data to impersonate someone/something'},
        {'term': 'Hash', 'meaning': 'One-way cryptographic function to secure data'},
        {'term': 'Salt', 'meaning': 'Random data added to password before hashing'},
        {'term': 'Certificate Authority', 'meaning': 'Trusted entity that issues digital certificates'},
        {'term': 'SOC', 'meaning': 'Security Operations Center - centralized security monitoring'},
        {'term': 'Threat Intelligence', 'meaning': 'Information about potential cyber threats'},
        {'term': 'Incident Response', 'meaning': 'Process of handling security breaches'},
        {'term': 'Forensics', 'meaning': 'Investigation of digital evidence'},
        {'term': 'Compliance', 'meaning': 'Adhering to security regulations and standards'},
        {'term': 'Risk Assessment', 'meaning': 'Process of identifying and evaluating security risks'},
        {'term': 'Vulnerability', 'meaning': 'Weakness that can be exploited by attackers'},
        {'term': 'Exploit', 'meaning': 'Code that takes advantage of a vulnerability'},
        {'term': 'Patch', 'meaning': 'Update that fixes security vulnerabilities'},
        {'term': 'Endpoint', 'meaning': 'Device connected to network (computer, phone, etc.)'},
        {'term': 'Sandbox', 'meaning': 'Isolated environment for testing suspicious code'},
        {'term': 'Proxy', 'meaning': 'Intermediate server that forwards requests'},
        {'term': 'TLS', 'meaning': 'Transport Layer Security - encryption protocol'},
        {'term': 'Cipher', 'meaning': 'Algorithm for performing encryption/decryption'},
        {'term': 'Payload', 'meaning': 'Part of malware that performs malicious action'},
        {'term': 'CVE', 'meaning': 'Common Vulnerabilities and Exposures - vulnerability database'}
    ]
    return jsonify(terms)

# Practice Platforms
@app.route('/api/practice-platforms')
def practice_platforms():
    return jsonify([
        {'name': 'HackTheBox', 'url': 'https://www.hackthebox.com', 'description': 'Realistic penetration testing labs and CTF challenges', 'type': 'Free + Paid', 'difficulty': 'Intermediate-Advanced'},
        {'name': 'TryHackMe', 'url': 'https://tryhackme.com', 'description': 'Beginner-friendly hacking rooms with guided learning paths', 'type': 'Free + Paid', 'difficulty': 'Beginner-Intermediate'},
        {'name': 'OverTheWire', 'url': 'https://overthewire.org', 'description': 'Wargames for learning security concepts through challenges', 'type': 'Free', 'difficulty': 'Beginner-Advanced'},
        {'name': 'PicoCTF', 'url': 'https://picoctf.org', 'description': 'Capture the flag competition platform for all skill levels', 'type': 'Free', 'difficulty': 'Beginner-Intermediate'},
        {'name': 'PortSwigger Web Security', 'url': 'https://portswigger.net/web-security', 'description': 'Free web security academy with interactive labs', 'type': 'Free', 'difficulty': 'All Levels'},
        {'name': 'Hacker101', 'url': 'https://www.hacker101.com', 'description': 'Free web security classes from HackerOne', 'type': 'Free', 'difficulty': 'Beginner'},
        {'name': 'CTFtime', 'url': 'https://ctftime.org', 'description': 'CTF team rankings and upcoming competitions', 'type': 'Free', 'difficulty': 'All Levels'},
        {'name': 'VulnHub', 'url': 'https://www.vulnhub.com', 'description': 'Vulnerable VM machines for practice', 'type': 'Free', 'difficulty': 'Intermediate-Advanced'},
        {'name': 'Root-Me', 'url': 'https://www.root-me.org', 'description': 'Platform for hacking and security challenges', 'type': 'Free', 'difficulty': 'All Levels'},
        {'name': 'CyberChef', 'url': 'https://gchq.github.io/CyberChef/', 'description': 'Web app for encryption, encoding, and analysis', 'type': 'Free', 'difficulty': 'Beginner'}
    ])

# Resume Tips
@app.route('/api/resume-tips')
def resume_tips():
    return jsonify({
        'key_skills': [
            'Network Security', 'Incident Response', 'SIEM Tools', 'Penetration Testing',
            'Risk Assessment', 'Compliance (ISO 27001, GDPR)', 'Cloud Security', 'Python/Scripting',
            'Vulnerability Management', 'Security Operations', 'Firewall Management', 'IDS/IPS',
            'Security Auditing', 'Threat Intelligence', 'Digital Forensics'
        ],
        'structure': [
            'Header: Name + Contact + LinkedIn/GitHub',
            'Professional Summary: 2-3 lines highlighting expertise and achievements',
            'Technical Skills: Categorized (Network, Cloud, Tools, Programming)',
            'Experience: Reverse chronological with achievements (not just duties)',
            'Certifications: List with dates (CISSP, CEH, Security+, etc.)',
            'Education: Degree + Institution + Year + GPA (if good)',
            'Projects: Highlight security-related projects with links',
            'Achievements: CTF rankings, Bug bounties, Publications'
        ],
        'common_mistakes': [
            'Generic objective statements instead of professional summary',
            'Listing duties instead of achievements with metrics',
            'Typos and formatting issues',
            'Too long (>2 pages for experienced, >1 for freshers)',
            'Missing certifications or projects',
            'Not tailoring resume for specific job roles',
            'Using unprofessional email addresses'
        ],
        'action_words': [
            'Implemented', 'Secured', 'Monitored', 'Responded', 'Analyzed',
            'Developed', 'Mitigated', 'Configured', 'Investigated', 'Managed',
            'Deployed', 'Optimized', 'Collaborated', 'Led', 'Designed',
            'Architected', 'Automated', 'Audited', 'Documented', 'Trained'
        ]
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
