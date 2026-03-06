import os
import time
from PIL import Image, ImageFilter

def process_image(input_path, output_dir="output"):
    """Execute image processing tasks and return the time taken."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_name = os.path.basename(input_path)
    base_name = os.path.splitext(file_name)[0]
    
    print(f"Start processing: {file_name} ...")
    start_time = time.time()
    
    try:
        with Image.open(input_path) as img:
            # 1. Scaling (Resize to 50%)
            res_img = img.resize((img.width // 2, img.height // 2))
            res_img.save(os.path.join(output_dir, f"{base_name}_resized.jpg"))
            
            # 2. Grayscale conversion (Grayscale)
            gray_img = img.convert("L")
            gray_img.save(os.path.join(output_dir, f"{base_name}_gray.jpg"))
            
            # 3. Filters (Gaussian Blur)
            blur_img = img.filter(ImageFilter.GaussianBlur(radius=2))
            blur_img.save(os.path.join(output_dir, f"{base_name}_blurred.jpg"))
            
        end_time = time.time()
        duration = end_time - start_time
        print(f"✅ Successfully processed {file_name}, took: {duration:.4f} seconds\n")
        return duration
    except Exception as e:
        print(f"❌ Error occurred while processing {file_name}: {e}\n")
        return None

if __name__ == "__main__":
    # This code block only runs during local testing.
    dataset_path = "dataset"
    if not os.path.exists(dataset_path) or not os.listdir(dataset_path):
        print(f"❌ Error: Please place test images in the {dataset_path} directory.")
    else:
        print("=== Start Local Image Processing Test ===")
        for img_name in os.listdir(dataset_path):
            if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                process_image(os.path.join(dataset_path, img_name))
        print("=== Test completed, please check the output/ directory ===")