import cv2 as cv
import torch
from PIL import Image
from facenet.models.mtcnn import MTCNN
from utils.distance import *
from utils.functions import *
from verification_models import VGGFace2

def face_matching(
    face1, face2, model: torch.nn.Module, distance_metric_name, model_name, device="cpu"
):
    assert model_name == "VGG-Face2", f"{model_name} is not supported"
    
    distance_metric = {
        "cosine": Cosine_Distance,
        "L1": L1_Distance,
        "euclidean": Euclidean_Distance,
    }
    
    distance_func = distance_metric.get(distance_metric_name, Euclidean_Distance)
    
    # Use device from model's parameters instead of calling device()
    device = next(model.parameters()).device
    
    face1 = face_transform(face1, model_name=model_name, device=device)
    face2 = face_transform(face2, model_name=model_name, device=device)
    
    result1 = model(face1)
    result2 = model(face2)
    
    dis = distance_func(result1, result2)
    
    threshold = findThreshold(
        model_name=model_name, distance_metric=distance_metric_name
    )
    return dis < threshold

def verify(
    img1: np.ndarray,
    img2: np.ndarray,
    detector_model: MTCNN,
    verifier_model,
    model_name="VGG-Face2",
):
    face1, box1, landmarks = extract_face(img1, detector_model, padding=1)
    face2, box2, landmarks = extract_face(img2, detector_model, padding=1)
    
    verified = face_matching(
        face1,
        face2,
        verifier_model,
        distance_metric_name="euclidean",
        model_name=model_name,
    )
    
    return verified

if __name__ == "__main__":
    filename1 = "images/thanh2.png"
    filename2 = "images/thanh4.jpg"
    
    image1 = get_image(filename1)
    image2 = get_image(filename2)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    detector_model = MTCNN(device=device)
    verifier_model = VGGFace2.load_model(device=device)
    
    results = verify(image1, image2, detector_model, verifier_model)
    print(results)