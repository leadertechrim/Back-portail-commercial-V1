from flask import Flask, jsonify
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# Configuration avec tes informations Cloudinary
cloudinary.config(
    cloud_name="dskdortsz",  
    api_key="843918322767789",          
    api_secret="CEgn2u-KoQyfCFmiGcv48125tYc"
)


@app.route('/')
def index():
    return jsonify({"message": "API Flask fonctionne"})

@app.route('/test_cloudinary')
def test_cloudinary():
    try:
        import os
        # Vérifier si le fichier existe
        file_path = "EmamaCV.pdf"
        if not os.path.exists(file_path):
            return jsonify({
                "success": False, 
                "error": f"Le fichier {file_path} n'existe pas"
            })
        
        print(f"Tentative d'upload avec les nouvelles credentials...")
        print(f"Cloud name: {cloudinary.config().cloud_name}")
        print(f"API Key: {cloudinary.config().api_key}")
        
        result = cloudinary.uploader.upload(
            file_path,
            public_id="test_folder/EmamaCV",
            resource_type="raw",
            access_mode="public",
            overwrite=True
        )
        
        print(f"Upload réussi: {result['secure_url']}")
        return jsonify({
            "success": True, 
            "url": result['secure_url'],
            "public_id": result['public_id']
        })
    except Exception as e:
        print(f"Erreur: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

file_path = "EmamaCV.pdf"
file_name = "EmamaCV"

def upload_pdf(file_path, file_name):
    try:
        result = cloudinary.uploader.upload(
            file_path,
            public_id=f"test_folder/{file_name}",
            resource_type="raw",
            access_mode="public",  # Force l'accès public
            overwrite=True
        )
        # URL publique
        url = result.get("secure_url")
        print(f"Upload réussi: {url}")
        return url
    except Exception as e:
        print(f"Erreur lors de l'upload: {str(e)}")
        return None

if __name__ == "__main__":
    app.run(debug=True)