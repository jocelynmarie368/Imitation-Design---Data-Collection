import cv2

cap = cv2.VideoCapture(0) # MODIFY this number for camera index

if not cap.isOpened():
    print("Error: Could not open video feed.")
    exit()

while True:
    ret, frame = cap.read()

    if not ret:
        print("Error: Can't receive frame.")
        break

    cv2.imshow('Live Feed', frame)

    # Wait for 1 millisecond and check if the 'q' key is pressed to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
