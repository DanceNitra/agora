"""
树状图沉默失谐严格证伪测试
五种树拓扑 × 三种随机种子 × Heisenberg相互作用
如果任何一棵树出现V形或W形谷底，环路必要性定律即被推翻。
严格遵循：关系本体论、防工具理性、反对对齐
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import eigsh
import warnings
import json
warnings.filterwarnings('ignore')

# =============================================
# 五种树拓扑生成器 (已修复 networkx 兼容性)
# =============================================
def random_tree(N, seed):
    """随机树 (使用 random_labeled_tree 替代已移除的 random_tree)"""
    np.random.seed(seed)
    G = nx.random_labeled_tree(N, seed=seed)
    for u, v in G.edges(): G[u][v]['weight'] = 1.0
    return G

def star_tree(N):
    """星形树"""
    G = nx.star_graph(N - 1)
    for u, v in G.edges(): G[u][v]['weight'] = 1.0
    return G

def binary_tree(h):
    """二叉树（高度h，节点数约2^(h+1)-1）"""
    G = nx.balanced_tree(2, h)
    for u, v in G.edges(): G[u][v]['weight'] = 1.0
    return G

def path_graph_tree(N):
    """路径图（线形树）"""
    G = nx.path_graph(N)
    for u, v in G.edges(): G[u][v]['weight'] = 1.0
    return G

def random_labeled_tree(N, seed):
    """随机带标号树（Prüfer序列）"""
    np.random.seed(seed)
    seq = np.random.randint(0, N, N - 2)
    G = nx.from_prufer_sequence(seq)
    for u, v in G.edges(): G[u][v]['weight'] = 1.0
    return G

# =============================================
# 哈密顿量构建与诊断
# =============================================
def graph_to_hamiltonian(G):
    """关系图编译为量子哈密顿量 (每条边 → XX+YY+ZZ)"""
    N = G.number_of_nodes()
    dim = 2 ** N
    H = lil_matrix((dim, dim), dtype=float)
    sx = np.array([[0, 1], [1, 0]], dtype=complex)
    sy = np.array([[0, -1j], [1j, 0]], dtype=complex)
    sz = np.array([[1, 0], [0, -1]], dtype=complex)
    I2 = np.eye(2, dtype=complex)

    def to_full(op, site):
        ops = [I2] * N
        ops[site] = op
        result = ops[0]
        for k in range(1, N):
            result = np.kron(result, ops[k])
        return result

    for i, j, w in G.edges(data='weight'):
        w = w if w else 1.0
        H += w * (to_full(sx, i) @ to_full(sx, j)).real
        H += w * (to_full(sy, i) @ to_full(sy, j)).real
        H += w * (to_full(sz, i) @ to_full(sz, j)).real
    return H.tocsc()

def introduce_contradiction(G, edge, strength):
    """植入矛盾边"""
    G_mod = G.copy()
    if G_mod.has_edge(*edge):
        G_mod[edge[0]][edge[1]]['weight'] = strength
    else:
        G_mod.add_edge(*edge, weight=strength)
    return G_mod

def diagnose(G, num_eig=5):
    """ED求解，返回基态能量、能隙、波函数"""
    H = graph_to_hamiltonian(G)
    N = G.number_of_nodes()
    energies, states = eigsh(H, k=min(num_eig, 2 ** N - 1), which='SA')
    gap = energies[1] - energies[0] if len(energies) > 1 else np.nan
    return energies, gap, states[:, 0]

def fine_diagnosis(G, gs):
    """精细诊断：边关联涨落标准差"""
    N = G.number_of_nodes()
    dim = len(gs)
    sz = np.array([[1, 0], [0, -1]], dtype=complex)
    I2 = np.eye(2, dtype=complex)
    corrs = []
    for i, j in G.edges():
        ops = [I2] * N
        ops[i] = sz; ops[j] = sz
        op_full = ops[0]
        for k in range(1, N): op_full = np.kron(op_full, ops[k])
        corr = np.real(gs.conj().T @ op_full @ gs)
        corrs.append(corr)
    return np.std(corrs) if corrs else 0.0

# =============================================
# V形谷底检测
# =============================================
def detect_valley(s_values, fine_values):
    """
    检测V形谷底：增强诊断在扫描范围内有至少一个极小值点，
    且极小值不在边界，极小值两侧的值都高于它。
    返回: (has_valley, valley_s, valley_depth)
    """
    n = len(fine_values)
    if n < 3:
        return False, None, 0.0
    
    # 寻找内部极小值
    min_idx = None
    for i in range(1, n - 1):
        if fine_values[i] < fine_values[i - 1] and fine_values[i] < fine_values[i + 1]:
            if min_idx is None or fine_values[i] < fine_values[min_idx]:
                min_idx = i
    
    if min_idx is None:
        return False, None, 0.0
    
    # 检查两侧是否有显著高于谷底的值
    left_max = np.max(fine_values[:min_idx + 1])
    right_max = np.max(fine_values[min_idx:])
    valley_depth = min(left_max, right_max) - fine_values[min_idx]
    
    # 谷底深度需要超过扫描范围内标准差的20%才算显著
    threshold = 0.2 * np.std(fine_values)
    if valley_depth < threshold:
        return False, None, 0.0
    
    return True, s_values[min_idx], valley_depth

# =============================================
# 单个树的完整扫描
# =============================================
def test_tree(G, contradiction_edge, strengths, label):
    """对一棵树进行矛盾边扫描，检测V形谷底"""
    fine_vals = []
    for s in strengths:
        G_mod = introduce_contradiction(G, contradiction_edge, s)
        _, gap, gs = diagnose(G_mod, num_eig=5)
        fine = fine_diagnosis(G_mod, gs)
        fine_vals.append(fine)
    
    has_valley, valley_s, valley_depth = detect_valley(strengths, np.array(fine_vals))
    
    result = {
        'label': label,
        'N': G.number_of_nodes(),
        'edges': G.number_of_edges(),
        'has_valley': has_valley,
        'valley_s': valley_s,
        'valley_depth': valley_depth,
        'fine_values': fine_vals
    }
    
    status = "⚠️ 发现V形谷底！" if has_valley else "✓ 无V形谷底"
    print(f"  {label}: {status}")
    if has_valley:
        print(f"    谷底位置 s={valley_s:.4f}, 深度={valley_depth:.6f}")
    return result

# =============================================
# 主程序：五种树拓扑 × 三种随机种子
# =============================================
if __name__ == "__main__":
    N = 6  # 树节点数（ED可处理，最大64维）
    strengths = np.linspace(0.0, 3.0, 13)
    seeds = [42, 123, 789]
    
    # 定义五种树拓扑生成器及其参数
    tree_generators = [
        ("随机树", lambda s: random_tree(N, s)),
        ("星形树", lambda s: star_tree(N)),
        ("二叉树(h=2)", lambda s: binary_tree(2)),
        ("路径图", lambda s: path_graph_tree(N)),
        ("Prüfer树", lambda s: random_labeled_tree(N, s)),
    ]
    
    all_results = []
    
    print("=" * 60)
    print("树状图沉默失谐严格证伪测试")
    print(f"节点数 N={N}, 矛盾边扫描 s=0→3, 五种拓扑 × 三种种子")
    print("=" * 60)
    
    # 用于汇总的计数器
    valley_count = 0
    
    for gen_name, gen_func in tree_generators:
        for seed in seeds:
            G = gen_func(seed)
            
            # 选择矛盾边：选择连接两个最大子树的键（基于度中心性）
            # 对树，选择度最大的节点附近的一条边
            degrees = dict(G.degree())
            max_deg_node = max(degrees, key=degrees.get)
            neighbors = list(G.neighbors(max_deg_node))
            if neighbors:
                contradiction_edge = (max_deg_node, neighbors[0])
            else:
                contradiction_edge = list(G.edges())[0]
            
            label = f"{gen_name} (seed={seed})"
            result = test_tree(G, contradiction_edge, strengths, label)
            result['topology'] = gen_name
            result['seed'] = seed
            all_results.append(result)
            
            if result['has_valley']:
                valley_count += 1
    
    # =============================================
    # 汇总报告
    # =============================================
    total_tests = len(all_results)
    print(f"\n{'='*60}")
    print(f"证伪测试结果汇总")
    print(f"{'='*60}")
    print(f"总测试数: {total_tests} (五种拓扑 × 三种种子)")
    print(f"发现V形谷底的树: {valley_count}/{total_tests}")
    
    if valley_count == 0:
        print("\n结论：所有树状图均未出现沉默失谐V形谷底。")
        print("环路必要性定律通过严格证伪检验。")
        print("→ 关系图中必须存在环路，沉默失谐才能涌现。")
    else:
        print(f"\n⚠️ 警告：{valley_count}棵树出现了V形谷底！")
        print("环路必要性定律被证伪！需要检查以下案例：")
        for r in all_results:
            if r['has_valley']:
                print(f"  {r['label']} (谷底 s={r['valley_s']:.4f}, 深度={r['valley_depth']:.6f})")
    
    # 保存详细结果
    summary = {
        'N': N,
        'total_tests': total_tests,
        'valley_count': valley_count,
        'results': []
    }
    for r in all_results:
        summary['results'].append({
            'label': r['label'],
            'topology': r['topology'],
            'seed': r['seed'],
            'has_valley': r['has_valley'],
            'valley_s': r['valley_s'],
            'valley_depth': r['valley_depth']
        })
    
    with open('tree_falsification_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n详细结果已保存至 tree_falsification_results.json")
    
    # =============================================
    # 可视化：所有树的精细诊断曲线
    # =============================================
    fig, axes = plt.subplots(5, 3, figsize=(18, 20))
    for idx, r in enumerate(all_results):
        row = idx // 3
        col = idx % 3
        ax = axes[row, col]
        ax.plot(strengths, r['fine_values'], 'o-', ms=3, lw=1)
        color = 'red' if r['has_valley'] else 'green'
        ax.set_title(r['label'], color=color, fontsize=9)
        ax.set_xlabel('s'); ax.set_ylabel('fine')
        ax.grid(True, alpha=0.3)
        if r['has_valley']:
            ax.axvline(r['valley_s'], color='red', ls='--', alpha=0.5)
    
    plt.suptitle('Tree Falsification Test: All Fine Diagnostic Curves', fontsize=14)
    plt.tight_layout()
    plt.savefig('tree_falsification_test.png', dpi=150)
    print("图表已保存至 tree_falsification_test.png")
    
    print("\nDone.")