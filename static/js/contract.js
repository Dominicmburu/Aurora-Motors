// =====================================================
// AURORA MOTORS - CONTRACT SIGNING
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeContractSigning();
    initializeSignaturePad();
    initializeContractReview();
});

// =====================================================
// CONTRACT SIGNING INITIALIZATION
// =====================================================
function initializeContractSigning() {
    const contractModal = document.getElementById('contract-modal');
    const signContractBtn = document.getElementById('sign-contract-btn');
    
    if (signContractBtn) {
        signContractBtn.addEventListener('click', function() {
            showContractModal();
        });
    }
    
    // Close modal events
    const closeButtons = document.querySelectorAll('.close-contract');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', hideContractModal);
    });
    
    // Close on outside click
    if (contractModal) {
        contractModal.addEventListener('click', function(e) {
            if (e.target === this) {
                hideContractModal();
            }
        });
    }
}

function showContractModal() {
    const modal = document.getElementById('contract-modal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        
        // Load contract content
        loadContractContent();
        
        // Initialize signature pad
        setTimeout(initializeSignaturePad, 100);
    }
}

function hideContractModal() {
    const modal = document.getElementById('contract-modal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

// =====================================================
// CONTRACT CONTENT LOADING
// =====================================================
function loadContractContent() {
    const contractContent = document.getElementById('contract-content');
    
    if (contractContent && !contractContent.innerHTML.trim()) {
        contractContent.innerHTML = `
            <div class="contract-header">
                <h2>Aurora Motors Car Rental Agreement</h2>
                <p class="contract-date">Date: ${new Date().toLocaleDateString()}</p>
            </div>
            
            <div class="contract-section">
                <h3>1. Rental Agreement Terms</h3>
                <p>This rental agreement ("Agreement") is entered into between Aurora Motors Pty Ltd ("Company") and the renter ("Renter") for the rental of the vehicle described below.</p>
            </div>
            
            <div class="contract-section">
                <h3>2. Vehicle Information</h3>
                <div class="vehicle-details">
                    <p><strong>Vehicle:</strong> <span id="contract-vehicle">[Vehicle details will be inserted]</span></p>
                    <p><strong>License Plate:</strong> <span id="contract-license">[License plate]</span></p>
                    <p><strong>VIN:</strong> <span id="contract-vin">[VIN number]</span></p>
                </div>
            </div>
            
            <div class="contract-section">
                <h3>3. Rental Period</h3>
                <p><strong>Pickup Date:</strong> <span id="contract-pickup">[Pickup date]</span></p>
                <p><strong>Return Date:</strong> <span id="contract-return">[Return date]</span></p>
                <p><strong>Pickup Location:</strong> <span id="contract-pickup-location">[Pickup location]</span></p>
                <p><strong>Return Location:</strong> <span id="contract-return-location">[Return location]</span></p>
            </div>
            
            <div class="contract-section">
                <h3>4. Rental Charges</h3>
                <div class="charges-table">
                    <div class="charge-row">
                        <span>Daily Rate:</span>
                        <span id="contract-daily-rate">$[Daily rate]</span>
                    </div>
                    <div class="charge-row">
                        <span>Number of Days:</span>
                        <span id="contract-days">[Number of days]</span>
                    </div>
                    <div class="charge-row">
                        <span>Subtotal:</span>
                        <span id="contract-subtotal">$[Subtotal]</span>
                    </div>
                    <div class="charge-row">
                        <span>Security Deposit:</span>
                        <span id="contract-deposit">$[Security deposit]</span>
                    </div>
                    <div class="charge-row total">
                        <span><strong>Total Amount:</strong></span>
                        <span id="contract-total"><strong>$[Total amount]</strong></span>
                    </div>
                </div>
            </div>
            
            <div class="contract-section">
                <h3>5. Renter Responsibilities</h3>
                <ul>
                    <li>The Renter must be at least 21 years of age and hold a valid driver's license.</li>
                    <li>The Renter agrees to use the vehicle in a careful and responsible manner.</li>
                    <li>The Renter is responsible for all traffic violations, fines, and penalties.</li>
                    <li>The vehicle must be returned with the same amount of fuel as when rented.</li>
                    <li>Smoking is strictly prohibited in all vehicles.</li>
                    <li>The Renter must report any accidents or damage immediately.</li>
                </ul>
            </div>
            
            <div class="contract-section">
                <h3>6. Insurance Coverage</h3>
                <p>The rental includes comprehensive insurance coverage with a deductible as specified in the rental terms. The Renter is responsible for the deductible amount in case of damage.</p>
            </div>
            
            <div class="contract-section">
                <h3>7. Prohibited Uses</h3>
                <ul>
                    <li>Racing, speed testing, or any competitive driving</li>
                    <li>Transporting illegal substances or materials</li>
                    <li>Subletting or unauthorized use by others</li>
                    <li>Off-road driving (unless specifically authorized)</li>
                    <li>Towing any vehicle or trailer</li>
                </ul>
            </div>
            
            <div class="contract-section">
                <h3>8. Cancellation Policy</h3>
                <p>Cancellations made more than 48 hours before pickup time will receive a full refund. Cancellations made within 48 hours may be subject to cancellation fees.</p>
            </div>
            
            <div class="contract-section">
                <h3>9. Agreement</h3>
                <p>By signing below, the Renter acknowledges having read, understood, and agreed to all terms and conditions of this rental agreement.</p>
            </div>
        `;
        
        // Populate contract with actual booking data
        populateContractData();
    }
}

function populateContractData() {
    // Get booking data from the page or API
    const bookingData = getBookingData();
    
    if (bookingData) {
        // Populate vehicle information
        const vehicleElement = document.getElementById('contract-vehicle');
        if (vehicleElement) vehicleElement.textContent = bookingData.vehicle_name;
        
        const licenseElement = document.getElementById('contract-license');
        if (licenseElement) licenseElement.textContent = bookingData.license_plate;
        
        const vinElement = document.getElementById('contract-vin');
        if (vinElement) vinElement.textContent = bookingData.vin_number;
        
        // Populate rental period
        const pickupElement = document.getElementById('contract-pickup');
        if (pickupElement) pickupElement.textContent = formatDateTime(bookingData.pickup_date);
        
        const returnElement = document.getElementById('contract-return');
        if (returnElement) returnElement.textContent = formatDateTime(bookingData.return_date);
        
        const pickupLocationElement = document.getElementById('contract-pickup-location');
        if (pickupLocationElement) pickupLocationElement.textContent = bookingData.pickup_location;
        
        const returnLocationElement = document.getElementById('contract-return-location');
        if (returnLocationElement) returnLocationElement.textContent = bookingData.return_location;
        
        // Populate charges
        const dailyRateElement = document.getElementById('contract-daily-rate');
        if (dailyRateElement) dailyRateElement.textContent = `$${bookingData.daily_rate}`;
        
        const daysElement = document.getElementById('contract-days');
        if (daysElement) daysElement.textContent = bookingData.total_days;
        
        const subtotalElement = document.getElementById('contract-subtotal');
        if (subtotalElement) subtotalElement.textContent = `$${bookingData.subtotal}`;
        
        const depositElement = document.getElementById('contract-deposit');
        if (depositElement) depositElement.textContent = `$${bookingData.security_deposit}`;
        
        const totalElement = document.getElementById('contract-total');
        if (totalElement) totalElement.textContent = `$${bookingData.total_amount}`;
    }
}

function getBookingData() {
    // This would typically come from the server or be embedded in the page
    // For now, return dummy data
    return {
        vehicle_name: '2024 Toyota Camry',
        license_plate: 'ABC123',
        vin_number: '1HGBH41JXMN109186',
        pickup_date: new Date().toISOString(),
        return_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
        pickup_location: 'Sydney Airport',
        return_location: 'Sydney Airport',
        daily_rate: 89,
        total_days: 3,
        subtotal: 267,
        security_deposit: 500,
        total_amount: 767
    };
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-AU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// =====================================================
// SIGNATURE PAD FUNCTIONALITY
// =====================================================
function initializeSignaturePad() {
    const canvas = document.getElementById('signature-canvas');
    const clearBtn = document.getElementById('clear-signature');
    const signBtn = document.getElementById('submit-signature');
    
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    let isDrawing = false;
    let hasSignature = false;
    
    // Set canvas size
    resizeCanvas();
    
    // Drawing functions
    function startDrawing(e) {
        isDrawing = true;
        draw(e);
    }
    
    function draw(e) {
        if (!isDrawing) return;
        
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        
        let x, y;
        
        if (e.type.includes('touch')) {
            x = (e.touches[0].clientX - rect.left) * scaleX;
            y = (e.touches[0].clientY - rect.top) * scaleY;
        } else {
            x = (e.clientX - rect.left) * scaleX;
            y = (e.clientY - rect.top) * scaleY;
        }
        
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.strokeStyle = '#1B365D';
        
        ctx.lineTo(x, y);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x, y);
        
        hasSignature = true;
        updateSignatureButtons();
    }
    
    function stopDrawing() {
        if (isDrawing) {
            isDrawing = false;
            ctx.beginPath();
        }
    }
    
    function resizeCanvas() {
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * window.devicePixelRatio;
        canvas.height = rect.height * window.devicePixelRatio;
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    }
    
    function clearSignature() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        hasSignature = false;
        updateSignatureButtons();
    }
    
    function updateSignatureButtons() {
        if (clearBtn) clearBtn.disabled = !hasSignature;
        if (signBtn) signBtn.disabled = !hasSignature;
    }
    
    // Mouse events
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseout', stopDrawing);
    
    // Touch events
    canvas.addEventListener('touchstart', function(e) {
        e.preventDefault();
        startDrawing(e);
    });
    
    canvas.addEventListener('touchmove', function(e) {
        e.preventDefault();
        draw(e);
    });
    
    canvas.addEventListener('touchend', function(e) {
        e.preventDefault();
        stopDrawing();
    });
    
    // Button events
    if (clearBtn) {
        clearBtn.addEventListener('click', clearSignature);
    }
    
    if (signBtn) {
        signBtn.addEventListener('click', submitSignature);
    }
    
    // Window resize
    window.addEventListener('resize', resizeCanvas);
    
    // Initial state
    updateSignatureButtons();
}

// =====================================================
// CONTRACT REVIEW
// =====================================================
function initializeContractReview() {
    const agreeCheckbox = document.getElementById('agree-terms');
    const submitBtn = document.getElementById('submit-signature');
    
    if (agreeCheckbox && submitBtn) {
        agreeCheckbox.addEventListener('change', function() {
            updateSubmitButton();
        });
    }
    
    function updateSubmitButton() {
        const hasAgreed = agreeCheckbox && agreeCheckbox.checked;
        const hasSignature = document.getElementById('signature-canvas') && 
                           hasSignatureData();
        
        if (submitBtn) {
            submitBtn.disabled = !hasAgreed || !hasSignature;
        }
    }
    
    // Check every second for signature updates
    setInterval(updateSubmitButton, 1000);
}

function hasSignatureData() {
    const canvas = document.getElementById('signature-canvas');
    if (!canvas) return false;
    
    const ctx = canvas.getContext('2d');
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    
    // Check if any pixel is not transparent
    for (let i = 3; i < imageData.data.length; i += 4) {
        if (imageData.data[i] !== 0) return true;
    }
    
    return false;
}

// =====================================================
// SIGNATURE SUBMISSION
// =====================================================
function submitSignature() {
    const canvas = document.getElementById('signature-canvas');
    const agreeCheckbox = document.getElementById('agree-terms');
    
    if (!canvas || !agreeCheckbox) return;
    
    if (!agreeCheckbox.checked) {
        AuroraMotors.showNotification('Please agree to the terms and conditions', 'error');
        return;
    }
    
    if (!hasSignatureData()) {
        AuroraMotors.showNotification('Please provide your signature', 'error');
        return;
    }
    
    // Get signature data
    const signatureData = canvas.toDataURL('image/png');
    
    // Show loading state
    const submitBtn = document.getElementById('submit-signature');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Submitting...';
    submitBtn.disabled = true;
    
    // Submit to server
    fetch('/api/contract/sign/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
            signature: signatureData,
            agree_terms: true,
            timestamp: new Date().toISOString()
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            AuroraMotors.showNotification('Contract signed successfully!', 'success');
            hideContractModal();
            
            // Redirect or update UI
            if (result.redirect_url) {
                setTimeout(() => {
                    window.location.href = result.redirect_url;
                }, 1500);
            }
        } else {
            AuroraMotors.showNotification(result.error || 'Failed to submit signature', 'error');
        }
    })
    .catch(error => {
        console.error('Signature submission error:', error);
        AuroraMotors.showNotification('An error occurred. Please try again.', 'error');
    })
    .finally(() => {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    });
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}