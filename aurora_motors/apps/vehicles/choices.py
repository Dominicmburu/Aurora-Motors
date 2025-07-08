"""Vehicle-related choices and constants"""

TRANSMISSION_CHOICES = (
    ('manual', 'Manual'),
    ('automatic', 'Automatic'),
    ('cvt', 'CVT'),
)

FUEL_TYPE_CHOICES = (
    ('petrol', 'Petrol'),
    ('diesel', 'Diesel'),
    ('hybrid', 'Hybrid'),
    ('electric', 'Electric'),
)

VEHICLE_STATUS_CHOICES = (
    ('available', 'Available'),
    ('rented', 'Rented'),
    ('maintenance', 'Under Maintenance'),
    ('out_of_service', 'Out of Service'),
)

CONDITION_CHOICES = (
    ('excellent', 'Excellent'),
    ('good', 'Good'),
    ('fair', 'Fair'),
    ('poor', 'Poor'),
)

FEATURE_TYPES = (
    ('safety', 'Safety'),
    ('comfort', 'Comfort'),
    ('technology', 'Technology'),
    ('performance', 'Performance'),
    ('convenience', 'Convenience'),
)

MAINTENANCE_TYPES = (
    ('service', 'Regular Service'),
    ('repair', 'Repair'),
    ('inspection', 'Inspection'),
    ('cleaning', 'Cleaning'),
    ('tire_change', 'Tire Change'),
    ('oil_change', 'Oil Change'),
    ('other', 'Other'),
)

# Vehicle categories
VEHICLE_CATEGORIES = [
    'Economy',
    'Compact',
    'Mid-size',
    'Full-size',
    'Premium',
    'Luxury',
    'SUV',
    'Premium SUV',
    'Minivan',
    'Pickup Truck',
    'Convertible',
    'Sports Car',
    'Electric',
    'Hybrid',
]

# Popular vehicle brands
VEHICLE_BRANDS = [
    'Toyota',
    'Honda',
    'Nissan',
    'Mazda',
    'Subaru',
    'Mitsubishi',
    'Hyundai',
    'Kia',
    'BMW',
    'Mercedes-Benz',
    'Audi',
    'Volkswagen',
    'Ford',
    'Holden',
    'Tesla',
]

# Common vehicle features
COMMON_FEATURES = [
    # Safety Features
    ('ABS Brakes', 'safety'),
    ('Airbags', 'safety'),
    ('Electronic Stability Control', 'safety'),
    ('Traction Control', 'safety'),
    ('Reverse Camera', 'safety'),
    ('Parking Sensors', 'safety'),
    ('Blind Spot Monitoring', 'safety'),
    ('Lane Departure Warning', 'safety'),
    
    # Comfort Features
    ('Air Conditioning', 'comfort'),
    ('Climate Control', 'comfort'),
    ('Leather Seats', 'comfort'),
    ('Heated Seats', 'comfort'),
    ('Power Seats', 'comfort'),
    ('Sunroof', 'comfort'),
    ('Cruise Control', 'comfort'),
    
    # Technology Features
    ('Bluetooth', 'technology'),
    ('USB Ports', 'technology'),
    ('Apple CarPlay', 'technology'),
    ('Android Auto', 'technology'),
    ('GPS Navigation', 'technology'),
    ('Premium Sound System', 'technology'),
    ('Touchscreen Display', 'technology'),
    ('Wireless Charging', 'technology'),
    
    # Performance Features
    ('Turbo Engine', 'performance'),
    ('All-Wheel Drive', 'performance'),
    ('Sport Mode', 'performance'),
    ('Paddle Shifters', 'performance'),
    
    # Convenience Features
    ('Keyless Entry', 'convenience'),
    ('Push Button Start', 'convenience'),
    ('Remote Start', 'convenience'),
    ('Power Windows', 'convenience'),
    ('Power Steering', 'convenience'),
    ('Automatic Lights', 'convenience'),
    ('Rain Sensing Wipers', 'convenience'),
]