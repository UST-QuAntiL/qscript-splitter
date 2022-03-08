import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit, Aer, transpile, assemble
from qiskit.visualization import plot_histogram
from math import gcd
from numpy.random import randint
import pandas as pd
from fractions import Fraction

print("Imports Successful")

N = 35
a = 3

# Calculate the plotting data
xvals = np.arange(35)
yvals = [np.mod(a ** x, N) for x in xvals]

# Use matplotlib to display it nicely
fig, ax = plt.subplots()
ax.plot(xvals, yvals, linewidth=1, linestyle='dotted', marker='x')
ax.set(xlabel='$x$', ylabel='$%i^x$ mod $%i$' % (a, N),
	   title="Example of Periodic Function in Shor's Algorithm")
try:  # plot r on the graph
	r = yvals[1:].index(1) + 1
	plt.annotate('', xy=(0, 1), xytext=(r, 1), arrowprops=dict(arrowstyle='<->'))
	plt.annotate('$r=%i$' % r, xy=(r / 3, 1.5))
except ValueError:
	print('Could not find period, check a < N and have no common factors.')

ax.set(xlabel='Number of applications of U', ylabel='End state of register',
	   title="Effect of Successive Applications of U")
fig




def c_amod15(a, power):
	"""Controlled multiplication by a mod 15"""
	if a not in [2, 7, 8, 11, 13]:
		raise ValueError("'a' must be 2,7,8,11 or 13")
	U = QuantumCircuit(4)
	for iteration in range(power):
		if a in [2, 13]:
			U.swap(0, 1)
			U.swap(1, 2)
			U.swap(2, 3)
		if a in [7, 8]:
			U.swap(2, 3)
			U.swap(1, 2)
			U.swap(0, 1)
		if a == 11:
			U.swap(1, 3)
			U.swap(0, 2)
		if a in [7, 11, 13]:
			for q in range(4):
				U.x(q)
	U = U.to_gate()
	U.name = "%i^%i mod 15" % (a, power)
	c_U = U.control()
	return c_U


"""We will use 8 counting qubits:"""

# Specify variables
n_count = 8  # number of counting qubits
a = 7

"""We also import the circuit for the QFT (you can read more about the QFT in the [quantum Fourier transform chapter](./quantum-fourier-transform.html#generalqft)):"""

def qft_dagger(n):
	"""n-qubit QFTdagger the first n qubits in circ"""
	qc = QuantumCircuit(n)
	# Don't forget the Swaps!
	for qubit in range(n // 2):
		qc.swap(qubit, n - qubit - 1)
	for j in range(n):
		for m in range(j):
			qc.cp(-np.pi / float(2 ** (j - m)), m, j)
		qc.h(j)
	qc.name = "QFT†"
	return qc


"""With these building blocks we can easily construct the circuit for Shor's algorithm:"""

# Create QuantumCircuit with n_count counting qubits
# plus 4 qubits for U to act on
qc = QuantumCircuit(n_count + 4, n_count)

# Initialize counting qubits
# in state |+>
for q in range(n_count):
	qc.h(q)

# And auxiliary register in state |1>
qc.x(3 + n_count)

# Do controlled-U operations
for q in range(n_count):
	qc.append(c_amod15(a, 2 ** q),
			  [q] + [i + n_count for i in range(4)])

# Do inverse-QFT
qc.append(qft_dagger(n_count), range(n_count))

# Measure circuit
qc.measure(range(n_count), range(n_count))
qc.draw(fold=-1)  # -1 means 'do not fold'

"""Let's see what results we measure:"""

aer_sim = Aer.get_backend('aer_simulator')
t_qc = transpile(qc, aer_sim)
qobj = assemble(t_qc)
results = aer_sim.run(qobj).result()
counts = results.get_counts()
plot_histogram(counts)

"""Since we have 8 qubits, these results correspond to measured phases of:"""

rows, measured_phases = [], []
for output in counts:
	decimal = int(output, 2)  # Convert (base 2) string to decimal
	phase = decimal / (2 ** n_count)  # Find corresponding eigenvalue
	measured_phases.append(phase)
	# Add these values to the rows in our table:
	rows.append([f"{output}(bin) = {decimal:>3}(dec)",
				 f"{decimal}/{2 ** n_count} = {phase:.2f}"])
# Print the rows in a table
headers = ["Register Output", "Phase"]
df = pd.DataFrame(rows, columns=headers)
print(df)

"""We can now use the continued fractions algorithm to attempt to find $s$ and $r$. Python has this functionality built in: We can use the `fractions` module to turn a float into a `Fraction` object, for example:"""

Fraction(0.666)

"""Because this gives fractions that return the result exactly (in this case, `0.6660000...`), this can give gnarly results like the one above. We can use the `.limit_denominator()` method to get the fraction that most closely resembles our float, with denominator below a certain value:"""

# Get fraction that most closely resembles 0.666
# with denominator < 15
Fraction(0.666).limit_denominator(15)

"""Much nicer! The order (r) must be less than N, so we will set the maximum denominator to be `15`:"""

rows = []
for phase in measured_phases:
	frac = Fraction(phase).limit_denominator(15)
	rows.append([phase, f"{frac.numerator}/{frac.denominator}", frac.denominator])
# Print as a table
headers = ["Phase", "Fraction", "Guess for r"]
df = pd.DataFrame(rows, columns=headers)
print(df)


def a2jmodN(a, j, N):
	"""Compute a^{2^j} (mod N) by repeated squaring"""
	for i in range(j):
		a = np.mod(a ** 2, N)
	return a


a2jmodN(7, 2049, 53)


N = 15

"""The first step is to choose a random number, $a$, between $1$ and $N-1$:"""

np.random.seed(1)  # This is to make sure we get reproduceable results
a = randint(2, 15)
print(a)

"""Next we quickly check it isn't already a non-trivial factor of $N$:"""

from math import gcd  # greatest common divisor

gcd(a, N)

"""Great. Next, we do Shor's order finding algorithm for `a = 7` and `N = 15`. Remember that the phase we measure will be $s/r$ where:

$$ a^r \bmod N = 1 $$

and $s$ is a random integer between 0 and $r-1$.
"""


def qpe_amod15(a):
	n_count = 8
	qc = QuantumCircuit(4 + n_count, n_count)
	for q in range(n_count):
		qc.h(q)  # Initialize counting qubits in state |+>
	qc.x(3 + n_count)  # And auxiliary register in state |1>
	for q in range(n_count):  # Do controlled-U operations
		qc.append(c_amod15(a, 2 ** q),
				  [q] + [i + n_count for i in range(4)])
	qc.append(qft_dagger(n_count), range(n_count))  # Do inverse-QFT
	qc.measure(range(n_count), range(n_count))
	# Simulate Results
	aer_sim = Aer.get_backend('aer_simulator')
	# Setting memory=True below allows us to see a list of each sequential reading
	t_qc = transpile(qc, aer_sim)
	qobj = assemble(t_qc, shots=1)
	result = aer_sim.run(qobj, memory=True).result()
	readings = result.get_memory()
	print("Register Reading: " + readings[0])
	phase = int(readings[0], 2) / (2 ** n_count)
	print("Corresponding Phase: %f" % phase)
	return phase


"""From this phase, we can easily find a guess for $r$:"""

phase = qpe_amod15(a)  # Phase = s/r
Fraction(phase).limit_denominator(15)  # Denominator should (hopefully!) tell us r

frac = Fraction(phase).limit_denominator(15)
s, r = frac.numerator, frac.denominator
print(r)

guesses = [gcd(a ** (r // 2) - 1, N), gcd(a ** (r // 2) + 1, N)]
print(guesses)

"""The cell below repeats the algorithm until at least one factor of 15 is found. You should try re-running the cell a few times to see how it behaves."""

a = 7
factor_found = False
attempt = 0
while not factor_found:
	attempt += 1
	print("\nAttempt %i:" % attempt)
	phase = qpe_amod15(a)  # Phase = s/r
	frac = Fraction(phase).limit_denominator(N)  # Denominator should (hopefully!) tell us r
	r = frac.denominator
	print("Result: r = %i" % r)
	if phase != 0:
		# Guesses for factors are gcd(x^{r/2} ±1 , 15)
		guesses = [gcd(a ** (r // 2) - 1, N), gcd(a ** (r // 2) + 1, N)]
		print("Guessed Factors: %i and %i" % (guesses[0], guesses[1]))
		for guess in guesses:
			if guess not in [1, N] and (N % guess) == 0:  # Check to see if guess is a factor
				print("*** Non-trivial factor found: %i ***" % guess)
				factor_found = True
