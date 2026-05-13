import face_recognition
import cv2
import numpy as np
import base64
import pickle
from io import BytesIO
from PIL import Image

# Threshold for face recognition matching (Euclidean distance)
FACE_DISTANCE_THRESHOLD = 0.45


def decode_image(image_data):
    """
    Decode base64-encoded image to OpenCV format (BGR).
    
    Args:
        image_data: Base64-encoded image string (may include data URI prefix)
    
    Returns:
        numpy.ndarray: OpenCV image in BGR format, or None if decode fails
    """
    try:
        # Handle data URI prefix (e.g., "data:image/jpeg;base64,...")
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_data)
        
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        
        # Decode to OpenCV format (BGR)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return img
    except Exception as e:
        print(f"Error decoding image: {str(e)}")
        return None


def encode_face(image_data):
    """
    Extract and encode a face from an image.
    
    Args:
        image_data: Base64-encoded image string
    
    Returns:
        numpy.ndarray: 128-dimensional face encoding, or None if no face detected
    """
    try:
        # Decode image
        img = decode_image(image_data)
        if img is None:
            return None
        
        # Convert BGR to RGB for face_recognition library
        rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Detect faces in image
        face_locations = face_recognition.face_locations(rgb_image, model='hog')
        
        if len(face_locations) == 0:
            print("No face detected in image")
            return None
        
        if len(face_locations) > 1:
            print(f"Multiple faces detected ({len(face_locations)}), using the first one")
        
        # Generate face encoding for the first detected face
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        if len(face_encodings) == 0:
            print("Could not generate face encoding")
            return None
        
        return face_encodings[0]
    except Exception as e:
        print(f"Error encoding face: {str(e)}")
        return None


def serialize_encoding(encoding):
    """
    Serialize a numpy face encoding to binary format for database storage.
    
    Args:
        encoding: 128-dimensional numpy array
    
    Returns:
        bytes: Pickled encoding
    """
    try:
        return pickle.dumps(encoding)
    except Exception as e:
        print(f"Error serializing encoding: {str(e)}")
        return None


def deserialize_encoding(encoding_bytes):
    """
    Deserialize a binary face encoding from database storage.
    
    Args:
        encoding_bytes: Pickled encoding bytes
    
    Returns:
        numpy.ndarray: 128-dimensional face encoding
    """
    try:
        return pickle.loads(encoding_bytes)
    except Exception as e:
        print(f"Error deserializing encoding: {str(e)}")
        return None


def recognize_face(image_data, stored_encoding):
    """
    Check if a face in an image matches a stored face encoding.
    
    Args:
        image_data: Base64-encoded image string
        stored_encoding: Stored face encoding (numpy array or bytes from database)
    
    Returns:
        tuple: (is_match: bool, distance: float)
    """
    try:
        # Deserialize stored encoding if it's bytes
        if isinstance(stored_encoding, bytes):
            stored_encoding = deserialize_encoding(stored_encoding)
        
        if stored_encoding is None:
            return False, None
        
        # Generate encoding from provided image
        test_encoding = encode_face(image_data)
        
        if test_encoding is None:
            return False, None
        
        # Calculate Euclidean distance
        distance = face_recognition.face_distance([stored_encoding], test_encoding)[0]
        
        # Check if distance is below threshold
        is_match = distance < FACE_DISTANCE_THRESHOLD
        
        return is_match, distance
    except Exception as e:
        print(f"Error in recognize_face: {str(e)}")
        return False, None


def find_best_match(image_data, candidates_dict):
    """
    Find the best matching student for an unknown face.
    
    Args:
        image_data: Base64-encoded image string
        candidates_dict: Dictionary {student_id: stored_encoding} of all registered faces
    
    Returns:
        tuple: (student_id: str, distance: float) or (None, None) if no match found
    """
    try:
        # Generate encoding from provided image
        test_encoding = encode_face(image_data)
        
        if test_encoding is None:
            return None, None
        
        if not candidates_dict:
            return None, None
        
        best_match_student = None
        best_distance = float('inf')
        
        # Compare against all registered faces
        for student_id, stored_encoding_bytes in candidates_dict.items():
            try:
                # Deserialize stored encoding
                stored_encoding = deserialize_encoding(stored_encoding_bytes)
                
                if stored_encoding is None:
                    continue
                
                # Calculate distance
                distance = face_recognition.face_distance([stored_encoding], test_encoding)[0]
                
                # Track best match
                if distance < best_distance:
                    best_distance = distance
                    best_match_student = student_id
            except Exception as e:
                print(f"Error comparing with student {student_id}: {str(e)}")
                continue
        
        # Return match only if below threshold
        if best_distance < FACE_DISTANCE_THRESHOLD:
            return best_match_student, best_distance
        else:
            return None, None
    except Exception as e:
        print(f"Error in find_best_match: {str(e)}")
        return None, None
