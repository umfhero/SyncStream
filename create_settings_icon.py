"""
Generate settings icon for SyncStream
"""

from PIL import Image, ImageDraw
import math

# Create a 128x128 image with transparency
size = 128
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Settings gear icon
center = size // 2
outer_radius = 50
inner_radius = 30
hole_radius = 15
num_teeth = 8

# Draw gear teeth
for i in range(num_teeth):
    angle1 = (i * 2 * math.pi) / num_teeth
    angle2 = ((i + 0.5) * 2 * math.pi) / num_teeth
    angle3 = ((i + 1) * 2 * math.pi) / num_teeth
    
    # Outer points
    x1 = center + outer_radius * math.cos(angle1)
    y1 = center + outer_radius * math.sin(angle1)
    x2 = center + outer_radius * math.cos(angle2)
    y2 = center + outer_radius * math.sin(angle2)
    x3 = center + outer_radius * math.cos(angle3)
    y3 = center + outer_radius * math.sin(angle3)
    
    # Inner points
    ix1 = center + inner_radius * math.cos(angle1)
    iy1 = center + inner_radius * math.sin(angle1)
    ix3 = center + inner_radius * math.cos(angle3)
    iy3 = center + inner_radius * math.sin(angle3)
    
    # Draw tooth
    draw.polygon(
        [(ix1, iy1), (x1, y1), (x2, y2), (x3, y3), (ix3, iy3)],
        fill=(100, 100, 100, 255)
    )

# Draw inner circle (body of gear)
draw.ellipse(
    [center - inner_radius, center - inner_radius,
     center + inner_radius, center + inner_radius],
    fill=(100, 100, 100, 255)
)

# Draw center hole
draw.ellipse(
    [center - hole_radius, center - hole_radius,
     center + hole_radius, center + hole_radius],
    fill=(0, 0, 0, 0)
)

# Save the icon
img.save('Assets/settings.png', 'PNG')
print("✓ Settings icon created: Assets/settings.png")
