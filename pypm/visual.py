import struct
from math import log2

import matplotlib.pyplot as plt


def get_data(file):
    with open(file, "rb") as f:
        content = f.read()
        data = struct.unpack(f"{len(content)//8}d", content)
    return data

def plot_mem_data(data, title="Memory Usage", xlabel="Time", ylabel="Usage"):
    units = ["B", "KB", "MB", "GB"]
    if len(data) == 0:
        avg = 0
    else:
        avg = sum(data)/len(data)
    if avg == 0:
        i = 0
    else:
        i = int(min(log2(avg)/10, 3))
        
    data = list(map(lambda x: x/2**(i*10), data))
    plt.plot(data)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(f"{ylabel} ({units[i]})")
    
def save_plot(data, file):
    plot_mem_data(data)
    plt.savefig(file)

if __name__ == "__main__":
    file = input()
    d = get_data(file)
    plot_mem_data(d)
    plt.show()
    save_plot(d, "plot.png")
