import pytest
from color_detector import _hue_to_color_name, correct_color_in_post
from image_matcher import (
    _extract_model_from_text,
    _extract_color_from_text,
    find_best_image,
)

def test_hue_to_color_name():
    # Green
    assert _hue_to_color_name(120, 0.5) == "سبز"
    # Blue
    assert _hue_to_color_name(210, 0.6) == "آبی"
    # Low saturation -> gray
    assert _hue_to_color_name(120, 0.05) == "خاکستری"
    # Low brightness -> black
    assert _hue_to_color_name(0, 0.2, avg_rgb=(20, 20, 20)) == "مشکی"

def test_correct_color_in_post():
    post = "📱 iPhone 15 Pro\n\nرنگ: مشکی\nظرفیت: 256GB"
    corrected = correct_color_in_post(post, "آبی تیتانیوم", threshold=0.55)
    assert "رنگ: آبی تیتانیوم" in corrected
    assert "ظرفیت: 256GB" in corrected

def test_extract_model_from_text():
    assert _extract_model_from_text("📱 iPhone 16 Pro Max\nرنگ: مشکی") == "16max"
    assert _extract_model_from_text("📱 iPhone 13\nرنگ: آبی") == "13normal"
    assert _extract_model_from_text("📱 iPhone 14 Pro\nرنگ: بنفش") == "14pro"
    assert _extract_model_from_text("گوشی ناشناخته") is None

def test_extract_color_from_text():
    colors = _extract_color_from_text("رنگ: مشکی و بدنه تمیز")
    assert "black" in colors or "meshki" in colors
    
    colors_blue = _extract_color_from_text("رنگ: آبی تیتانیوم")
    assert "blue" in colors_blue or "abi" in colors_blue

def test_find_best_image():
    post_text = "📱 iPhone 13 Pro\nرنگ: آبی\nظرفیت: 256GB"
    img_path = find_best_image(post_text)
    # If iphone/ catalog contains 13pro images, it should return a valid file path
    if img_path:
        import os
        assert os.path.exists(img_path)
