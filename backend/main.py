from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Union
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import logging
from datetime import datetime
import pytz
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv  # Import python-dotenv
import os  # Import os to access environment variables

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from React frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# MongoDB Connection
mongo_uri = os.getenv("MONGODB_URI")  # Fetch MongoDB URI from .env

if not mongo_uri:
    logging.error("❌ MONGODB_URI not found in .env file")
    raise HTTPException(status_code=500, detail="MongoDB URI not configured")

try:
    client = MongoClient(mongo_uri)
    db = client["pet_store"]
    pets_collection = db["pets"]
    logging.info("✅ MongoDB connected successfully")
except Exception as e:
    logging.error(f"❌ MongoDB connection error: {e}")
    raise HTTPException(status_code=500, detail="Database connection failed")

# Pet Model
class Pet(BaseModel):
    breed: str  # Changed from name to breed
    pet_type: str  # Changed from type to pet_type
    age: Optional[Union[int, float]] = None  # Allowing both int and float
    rate: float  # Price in INR
    description: Optional[str] = None
    image_url: Optional[str] = None

# Function to Convert MongoDB Document to JSON-Compatible Format
def pet_serializer(pet) -> dict:
    return {
        "id": str(pet["_id"]),  # Convert ObjectId to String
        "breed": pet["breed"],  # Updated field
        "pet_type": pet["pet_type"],  # Updated field
        "age": pet.get("age"),  # Now supports both int and float
        "rate": f"₹{pet['rate']:.2f}",  # Displaying rate in INR format
        "description": pet.get("description"),
        "image_url": pet.get("image_url"),
        "contact_number": "7036131241",  # Static contact number field
        "created_at": pet.get("created_at"),
        "updated_at": pet.get("updated_at"),
    }

# Create a New Pet
@app.post("/pets/", response_model=dict)
def create_pet(pet: Pet):
    try:
        pet_dict = pet.dict()
        ist = pytz.timezone("Asia/Kolkata")
        pet_dict["created_at"] = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")  # IST timestamp
        
        # Insert the pet into MongoDB
        result = pets_collection.insert_one(pet_dict)
        
        # Fetch the inserted document
        inserted_pet = pets_collection.find_one({"_id": result.inserted_id})
        
        if not inserted_pet:
            raise HTTPException(status_code=500, detail="Failed to retrieve inserted pet")
        
        # Serialize the inserted pet
        serialized_pet = pet_serializer(inserted_pet)
        
        logging.info(f"✅ Pet created with ID: {serialized_pet['id']}")
        
        return serialized_pet
    except Exception as e:
        logging.error(f"❌ Error creating pet: {e}")
        raise HTTPException(status_code=500, detail="Error creating pet")

# Retrieve All Pets
@app.get("/pets/", response_model=List[dict])
def get_pets():
    pets = list(pets_collection.find())
    return [pet_serializer(pet) for pet in pets]  # Serialize ObjectId

# Retrieve a Single Pet by ID
@app.get("/pets/{pet_id}", response_model=dict)
def get_pet(pet_id: str):
    try:
        obj_id = ObjectId(pet_id)  # Ensure it's a valid ObjectId
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid pet ID format")
    
    pet = pets_collection.find_one({"_id": obj_id})
    if pet:
        return pet_serializer(pet)
    raise HTTPException(status_code=404, detail="Pet not found")

# Update a Pet by ID
@app.put("/pets/{pet_id}", response_model=dict)
def update_pet(pet_id: str, updated_pet: Pet):
    try:
        obj_id = ObjectId(pet_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid pet ID format")
    
    pet_data = updated_pet.model_dump()  # Convert Pydantic model to dict
    ist = pytz.timezone("Asia/Kolkata")
    pet_data["updated_at"] = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")  # Update Timestamp

    result = pets_collection.update_one({"_id": obj_id}, {"$set": pet_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pet not found")

    updated_pet = pets_collection.find_one({"_id": obj_id})
    return pet_serializer(updated_pet)

# Delete a Pet by ID
@app.delete("/pets/{pet_id}")
def delete_pet(pet_id: str):
    try:
        obj_id = ObjectId(pet_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid pet ID format")
    
    result = pets_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pet not found")
    
    logging.info(f"🗑️ Pet deleted with ID: {pet_id}")
    return {"message": "Pet deleted successfully"}

# Delete All Pets
@app.delete("/pets/")
def delete_all_pets():
    result = pets_collection.delete_many({})
    logging.info(f"🗑️ Deleted {result.deleted_count} pets")
    return {"message": f"Deleted {result.deleted_count} pets successfully"}