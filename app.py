import os
import requests
import stripe
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION (O'zingizni kalitlaringizni qo'ying) ---
STABILITY_API_KEY = "YOUR_STABILITY_API_KEY"
STRIPE_SECRET_KEY = "sk_test_YOUR_STRIPE_KEY"
stripe.api_key = STRIPE_SECRET_KEY

# Stripe Dashboarddan olingan Price ID (Subscription uchun)
MONTHLY_PLAN_PRICE_ID = "price_1P..." 

@app.route('/generate-3d', methods=['POST'])
def generate_3d():
    if 'image' not in request.files:
        return jsonify({"error": "No image"}), 400
    
    img_file = request.files['image']
    style = request.form.get('style', 'gold')
    
    try:
        # 1. Format & Size Fix (1024x1024)
        img = Image.open(img_file.stream).convert('RGBA')
        img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
        
        canvas = Image.new('RGBA', (1024, 1024), (0, 0, 0, 255))
        img = Image.alpha_composite(canvas, img).convert('RGB')

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        prompts = {
            "gold": "Luxury 3D logo, solid 24k gold, polished metal, black background, 8k UHDR",
            "glass": "Translucent 3D glass logo, refraction, frosted finish, futuristic",
            "neon": "3D neon glowing sign logo, cyberpunk style, vibrant colors"
        }

        response = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image",
            headers={"Accept": "application/json", "Authorization": f"Bearer {STABILITY_API_KEY}"},
            files={"init_image": img_bytes},
            data={
                "image_strength": 0.35,
                "text_prompts[0][text]": prompts.get(style, prompts["gold"]),
                "cfg_scale": 12,
                "samples": 1,
            }
        )
        return response.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ONE TIME PAYMENT ($1.00) ---
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': 'Single 3D Render'}, 'unit_amount': 100}, 'quantity': 1}],
        mode='payment',
        success_url='http://127.0.0.1:5500/index.html?payment=success',
        cancel_url='http://127.0.0.1:5500/index.html',
    )
    return jsonify({'url': session.url})

# --- SUBSCRIPTION ($79.99/mo) ---
@app.route('/create-subscription', methods=['POST'])
def create_subscription():
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{'price': MONTHLY_PLAN_PRICE_ID, 'quantity': 1}],
        mode='subscription',
        success_url='http://127.0.0.1:5500/index.html?plan=pro',
        cancel_url='http://127.0.0.1:5500/index.html',
    )
    return jsonify({'url': session.url})

if __name__ == "__main__":
    app.run(port=5000, debug=True)