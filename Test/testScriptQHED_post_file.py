import qiskit
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import style
from qiskit.visualization import *
from qiskit.tools.monitor import job_monitor
from qiskit.compiler import transpile
from qiskit import IBMQ, QuantumCircuit, execute, display
def post(provider, backend, qc_small_h, qc_small_v, circ_list, qc_small_h_t, qc_small_v_t, circ_list_t, job, result, counts_h, counts_v, image, image_small, data_qb, anc_qb, total_qb, ): 

    # Extracting counts for odd-numbered states
    edge_scan_small_h = np.array([counts_h[f'{2*i+1:03b}'] for i in range(2**data_qb)]).reshape(2, 2)
    edge_scan_small_v = np.array([counts_v[f'{2*i+1:03b}'] for i in range(2**data_qb)]).reshape(2, 2).T
    edge_detected_image_small = edge_scan_small_h + edge_scan_small_v
    # Plotting the original and edge-detected images
    plt.title('Full Edge Detected Image')
    plt.xticks(range(edge_detected_image_small.shape[0]))
    plt.yticks(range(edge_detected_image_small.shape[1]))
    plt.imshow(edge_detected_image_small, extent=[0, edge_detected_image_small.shape[0], edge_detected_image_small.shape[1], 0], cmap='viridis')
    plt.show()
    return [edge_scan_small_h, edge_scan_small_v, edge_detected_image_small]
