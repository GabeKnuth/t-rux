from PyQt6.QtWidgets import QApplication, QWidget
import sys

print("Imported PyQt6")
app = QApplication(sys.argv)
w = QWidget()
w.show()
print("Created window")
# We won't run exec() to avoid blocking, just checking init
sys.exit(0)
