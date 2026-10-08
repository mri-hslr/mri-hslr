from PIL import Image
import cv2
import numpy as np

INPUT = "assets/no_background.png"

# ASCII characters from light → dark
RAMP = " .`:-=+*cs#%@"

COLS = 90
CHAR_ASPECT = 0.48


def image_to_ascii(path):
    # Load image with alpha channel
    img = Image.open(path).convert("RGBA")

    # Put transparent pixels onto a white background
    background = Image.new("RGBA", img.size, (255, 255, 255, 255))
    background.alpha_composite(img)

    # Convert to RGB
    img = background.convert("RGB")

    # Convert to OpenCV format
    img = np.array(img)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Calculate output height while compensating for character shape
    h, w = img.shape
    rows = max(1, int(COLS * (h / w) * CHAR_ASPECT))

    # Resize
    img = cv2.resize(img, (COLS, rows), interpolation=cv2.INTER_AREA)

    # Smooth while preserving edges
    img = cv2.bilateralFilter(
        img,
        d=7,
        sigmaColor=50,
        sigmaSpace=50
    )

    # Local contrast enhancement
    clahe = cv2.createCLAHE(
        clipLimit=3.0,
        tileGridSize=(8, 8)
    )

    img = clahe.apply(img)

    # Darkening curve
    img = img / 255.0
    img = np.power(img, 1.7)

    # Convert brightness to ASCII
    result = []

    for row in img:
        line = ""

        for value in row:
            index = int(value * (len(RAMP) - 1))
            line += RAMP[index]

        result.append(line)

    return "\n".join(result)


if __name__ == "__main__":
    ascii_art = image_to_ascii(INPUT)

    print(ascii_art)

    with open("assets/portrait.txt", "w") as f:
        f.write(ascii_art)

    print("\nSaved to assets/portrait.txt")

