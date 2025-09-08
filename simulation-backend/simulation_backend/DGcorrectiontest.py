#%%

import numpy as np
from scipy.io import loadmat
from scipy.signal import fftconvolve, resample
from scipy.fft import fft, ifft, fftshift
from math import log, pi
import matplotlib.pyplot as plt

def cconv_python(x, h):
    """
    MATLAB-like circular convolution:
    - Output length = len(x) + len(h) - 1
    - Circular (wrap-around) convolution
    """
    x = np.asarray(x)
    h = np.asarray(h)
    N = len(x) + len(h) - 1

    # Zero-pad both to length N
    x_padded = np.pad(x, (0, N - len(x)), mode='constant')
    h_padded = np.pad(h, (0, N - len(h)), mode='constant')

    # Perform circular convolution via FFT
    y = np.fft.ifft(np.fft.fft(x_padded) * np.fft.fft(h_padded)).real
    return y


def fftshift_matlab(x):
    """Emulate MATLAB's fftshift in Python (left-biased for even-length arrays)."""
    n = x.shape[-1]
    p2 = int(np.floor(n / 2))
    return np.roll(x, -p2, axis=-1)

def apply_resample(IRold, fs_new, fs_old):
    """Resamples the impulse response to the desired sampling frequency.

    Returns:
        IRnew (numpy.ndarray): see :attr:`IRnew`.
    """
    IRnew = resample(IRold, int(len(IRold) * fs_new / fs_old))
    return IRnew

def generate_blackman_windowed_sinc(lower_limit, upper_limit, sample_rate, M):
    x = np.arange(-0.5 * M, 0.5 * M + 1)
    x2 = np.arange(0, M + 1)
    
    fc = [lower_limit / sample_rate, upper_limit / sample_rate]
    A = []
    del_idx = np.where(x == 0)[0][0]  # index where x == 0
    
    for i in range(2):
        sinc_term = np.sin(2 * np.pi * fc[i] * x) / x
        sinc_term[del_idx] = 2 * np.pi * fc[i]  # replace NaN with limit value

        blackman_window = (0.42 - 0.5 * np.cos(2 * np.pi * x2 / M) +
                        0.08 * np.cos(4 * np.pi * x2 / M))
        
        A_row = sinc_term * blackman_window
        A_row = A_row / np.sum(A_row)
        
        if i == 1:
            A_row *= -1
            A_row[del_idx] += 1

        A.append(A_row)

    B = A[0] + A[1]
    B *= -1
    B[del_idx] += 1

    return B

def time_windowing(signal, Nleft, Nright):
    Nleft = int(np.ceil(Nleft))
    Nright = int(np.floor(Nright))
    
    nbt = len(signal)

    # Find first and last non-zero sample per row
    it0 = np.argmax(signal != 0)
    it3 = nbt - np.argmax(np.flip(signal) != 0)

    it1 = it0 + Nleft
    it2 = it3 - Nright

    t = np.arange(nbt)
    win = np.zeros_like(signal)

    if it1 > nbt: it1 = nbt
    if it2 > nbt: it2 = nbt

    if it1 > it0:
        win[it0:it1] = 0.5 * (1 - np.cos(
            pi / (it1 - it0) * (t[it0:it1] - t[it0])
        ))
    if it2 > it1:
        win[it1:it2] = 1
    if it3 > it2:
        win[it2:it3] = 0.5 * (1 + np.cos(
            pi / (it3 - it2) * (t[it2:it3] - t[it2])
        ))

    signal2 = signal * win
    return signal2

# DataTddg = loadmat('/Users/SilvinW/Library/CloudStorage/OneDrive-TUEindhoven/Files Wouter/wouter1ir.mat')["DataTddg"][0][0]
DataTddg = loadmat("/Users/SilvinW/repositories/CHORAS/backend/uploads/result.mat")

# Simulation Parameters
half_width = DataTddg["halfwidth"][0][0]
c0 = 343 #DataTddg["c0"][0][0]
S0 = 1

saved_every_n_samples = 1
fs_new = 1 / DataTddg["dt_new"][0][0]

ms_left = 5
ms_right = 100

# f_min_limit = 5
# f_max_limit = 50

# first_band_fmin = f_min_limit * 2.5
# last_band_fmax = fs_new * 0.666
f_min_limit = 20
f_max_limit = 200

first_band_fmin = 125 * 2**(-0.5)
last_band_fmax = 125 * 2**(0.5)

window_length = 10000

FWHM = 2 * half_width
alpha = 4 * log(2) / FWHM**2
dt_old = DataTddg["dt_old"][0][0] * saved_every_n_samples
fs_old = round(1 / dt_old)

irs_tddg = np.array(DataTddg["IR_Uncorrected"][0], dtype=np.float64)

# Resample if needed
if fs_old != fs_new:
    irs_tddg_new = apply_resample(irs_tddg, fs_new, fs_old)
else:
    irs_tddg_new = irs_tddg
    
# Frequency Domain Transform
n_samples = len(irs_tddg_new)
n_fft = 2**int(np.ceil(np.log2(n_samples * 2 - 1)))
n_zeros = n_fft - n_samples + 1
irs_tddg_new = np.pad(irs_tddg_new, (0, n_zeros), mode='constant')

TR_original = fft(irs_tddg_new) / fs_new
n_samples = len(TR_original)
df_new = fs_new / (n_samples - 1)
fv_tddg = np.arange(n_samples) * df_new

# Frequency domain correction
fv_tddg_shift = fftshift_matlab(fv_tddg - fs_new / 2)
omega = 2 * pi * fv_tddg_shift
beta_corr = 1 / (pi * S0) * alpha**(1.5) * c0**2 / (1j * np.sqrt(pi) * omega) * np.exp((omega / c0)**2 / (4 * alpha))
beta_corr[np.isinf(beta_corr)] = 0
beta_corr[np.isnan(beta_corr)] = 0

TR = TR_original * beta_corr
TR[0] = 0  # Remove 0 Hz component

# Frequency masking
index = ((fv_tddg >= f_min_limit) & (fv_tddg <= f_max_limit)) | \
        ((fv_tddg >= fs_new - f_max_limit) & (fv_tddg <= fs_new - f_min_limit))
index = ~index
TR[index] = 0

# IFFT
irs_tddg_corrected = ifft(TR).real * fs_new

# Generate filter window (assumed custom implementation)
blackman_windowed_sinc = generate_blackman_windowed_sinc(first_band_fmin, last_band_fmax, fs_new, window_length)

samples_left = int(ms_left * fs_new * 1e-3)
samples_right = int(ms_right * fs_new * 1e-3)

# Final IR construction
IRnew = np.zeros_like(irs_tddg_corrected)

this_ir = irs_tddg_corrected
this_ir_windowed = cconv_python(this_ir, blackman_windowed_sinc)
shift = -round(window_length / 2)
this_ir_windowed = np.roll(this_ir_windowed, shift)
this_ir_windowed = time_windowing(this_ir_windowed, samples_left, samples_right)
IRnew = this_ir_windowed

# Final FFT
tfs_final = fft(IRnew, axis=-1) / fs_new
n_samples = tfs_final.shape[-1]
df_new = fs_new / n_samples
fv_final = np.arange(n_samples) * df_new
fv_uncorrected = np.arange(TR_original.shape[-1]) * df_new
# %%
