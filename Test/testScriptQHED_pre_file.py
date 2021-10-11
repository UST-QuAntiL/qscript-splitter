import qiskit
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import style
from qiskit.visualization import *
from qiskit.tools.monitor import job_monitor
from qiskit.compiler import transpile
from qiskit import IBMQ, QuantumCircuit, execute, display
def pre(): 


    style.use('bmh')

    # A 8x8 binary image represented as a numpy array
    image = np.array([[0, 0, 0, 0, 0, 0, 0, 0],
                      [0, 1, 1, 1, 1, 1, 0, 0],
                      [0, 1, 1, 1, 1, 1, 1, 0],
                      [0, 1, 1, 1, 1, 1, 1, 0],
                      [0, 1, 1, 1, 1, 1, 1, 0],
                      [0, 0, 0, 1, 1, 1, 1, 0],
                      [0, 0, 0, 1, 1, 1, 1, 0],
                      [0, 0, 0, 0, 0, 0, 0, 0]])

    # Create a 2x2 image to be run on the hardware
    # The pixels in `image_small` correspond to the pixels at
    # (6, 2), (6, 3), (7, 2), (7, 3) respectively
    image_small = image[6:8, 2:4]


    # Initialize the number of qubits
    data_qb = 2
    anc_qb = 1
    total_qb = data_qb + anc_qb

    # Load the IBMQ account
    return [image, image_small, data_qb, anc_qb, total_qb]
