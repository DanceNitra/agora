"""
最终版 ED 常数验证 —— 内存安全版
只跑 N=12 和 N=14，遍历计算基矢构建稀疏矩阵，避免 np.kron 内存溢出。
"""
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import eigsh
import networkx as nx
import warnings
warnings.filterwarnings('ignore')

def chain_graph(N):
    G = nx.Graph()
    G.add_nodes_from(range(N))
    for i in range(N-1):
        G.add_edge(i, i+1, weight=1.0)
    return G

def graph_to_hamiltonian_sparse_memory_safe(G, D=0.0):
    """
    内存安全版哈密顿量构建。
    直接遍历计算基矢，填充稀疏矩阵，不产生密集中间数组。
    """
    N = G.number_of_nodes()
    dim = 2**N
    H = lil_matrix((dim, dim), dtype=float)

    for i, j, w in G.edges(data='weight'):
        w = w if w else 1.0
        for state in range(dim):
            bit_i = (state >> i) & 1
            bit_j = (state >> j) & 1

            # Heisenberg XX + YY (翻转两个自旋)
            flipped = state ^ (1 << i) ^ (1 << j)
            H[state, flipped] += w

            # Heisenberg ZZ (对角)
            if bit_i == bit_j:
                H[state, state] += w
            else:
                H[state, state] -= w

            # Rashba SOC (DM_y): D * (σ^z_i σ^x_j - σ^x_i σ^z_j)
            if D != 0.0:
                # σ^z_i σ^x_j 项
                # 只作用在 i 的 σ^z 和 j 的 σ^x 上
                # σ^z 在对角上：|0⟩ -> +1, |1⟩ -> -1
                # σ^x 在非对角上：翻转自旋
                sign_i = 1.0 if bit_i == 0 else -1.0
                # j 自旋翻转
                flipped_j = state ^ (1 << j)
                # 矩阵元 = D * sign_i * 1 (σ^x 的矩阵元是 1)
                H[state, flipped_j] += D * sign_i

                # -σ^x_i σ^z_j 项
                sign_j = 1.0 if bit_j == 0 else -1.0
                flipped_i = state ^ (1 << i)
                H[state, flipped_i] -= D * sign_j

    return H.tocsc()


def introduce_contradiction(G, edge, strength):
    G_mod = G.copy()
    if G_mod.has_edge(*edge):
        G_mod[edge[0]][edge[1]]['weight'] = strength
    else:
        G_mod.add_edge(edge[0], edge[1], weight=strength)
    return G_mod


def diagnose_memory_safe(G, D=0.0, num_eig=5):
    H = graph_to_hamiltonian_sparse_memory_safe(G, D=D)
    N = G.number_of_nodes()
    energies, states = eigsh(H, k=min(num_eig, 2**N - 1), which='SA')
    gap = energies[1] - energies[0] if len(energies) > 1 else np.nan
    return energies, gap, states[:, 0]


def fine_diagnosis(G, gs):
    N = G.number_of_nodes()
    dim = len(gs)
    corrs = []
    for i, j in G.edges():
        corr = 0.0
        for state in range(dim):
            prob = np.abs(gs[state]) ** 2
            bit_i = (state >> i) & 1
            bit_j = (state >> j) & 1
            corr += prob * (1 - 2 * bit_i) * (1 - 2 * bit_j)
        corrs.append(corr)
    return np.std(corrs) if corrs else 0.0


if __name__ == "__main__":
    strengths = np.linspace(0.0, 3.0, 9)
    D_val = 0.3
    results = []

    print("=== 最终版 ED 常数验证 (内存安全): N=12, 14 ===")
    for N in [12, 14]:
        G = chain_graph(N)
        center_edge = (N//2 - 1, N//2) if N % 2 == 1 else (N//2 - 1, N//2)
        print(f"\nN={N}, center_edge={center_edge}, dim={2**N}")

        fine_heis, fine_soc = [], []
        for s in strengths:
            print(f"  s={s:.2f}: Heisenberg...", end=' ', flush=True)
            G_heis = introduce_contradiction(G, center_edge, s)
            _, _, gs_heis = diagnose_memory_safe(G_heis, D=0.0, num_eig=5)
            fh = fine_diagnosis(G_heis, gs_heis)
            fine_heis.append(fh)
            print(f"fine={fh:.4f}", end='  SOC...', flush=True)

            G_soc = introduce_contradiction(G, center_edge, s)
            _, _, gs_soc = diagnose_memory_safe(G_soc, D=D_val, num_eig=5)
            fs = fine_diagnosis(G_soc, gs_soc)
            fine_soc.append(fs)
            print(f"fine={fs:.4f}", flush=True)

        fine_heis = np.array(fine_heis)
        fine_soc = np.array(fine_soc)
        ratios = fine_soc / fine_heis
        mean_r = np.mean(ratios)
        std_r = np.std(ratios, ddof=1)
        results.append({'N': N, 'mean': mean_r, 'std': std_r})
        print(f"  N={N}: mean ratio={mean_r:.6f}, std={std_r:.6f}")

        csv_name = f"constant_N{N}_ed_safe.csv"
        with open(csv_name, 'w') as f:
            f.write("strength,Heisenberg,SOC,ratio\n")
            for i, s in enumerate(strengths):
                f.write(f"{s:.2f},{fine_heis[i]:.6f},{fine_soc[i]:.6f},{ratios[i]:.6f}\n")
        print(f"  已保存: {csv_name}")

    with open('constant_validation_ed_final.csv', 'w') as f:
        f.write("N,mean_ratio,std_ratio\n")
        for r in results:
            f.write(f"{r['N']},{r['mean']:.6f},{r['std']:.6f}\n")

    print("\n全部完成。结果已保存至 constant_validation_ed_final.csv")