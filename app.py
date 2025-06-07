"""SS14 Displacement Map Creator
A GUI tool for creating displacement maps compatible with Space Station 14

Requirements: pip install tkinter pillow numpy
"""

from displacer.core import SS14DisplacementTool

if __name__ == "__main__":
    app = SS14DisplacementTool()
    app.run()

