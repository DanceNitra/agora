"""Projection of the MetaHuman face mesh into a viewport capture, and a smooth 2D warp of the mesh in
the orthographic frontal plane (X, Z) toward the reference landmarks. Depth (Y) is left unchanged."""
import numpy as np

ACTOR = np.array([0.0, 300000.0, 100000.0])
N_HEAD = 24049


def load_mesh(path="face_v.bin"):
    return np.fromfile(path, "<f4").reshape(-1, 3).astype(float)


def project(Vw, cam, rot, fov_deg, W, H):
    """World points -> pixel (u, v) for an Unreal camera. Returns uv and depth."""
    p, y = np.radians(rot["pitch"]), np.radians(rot["yaw"])
    fwd = np.array([np.cos(p) * np.cos(y), np.cos(p) * np.sin(y), np.sin(p)])
    right = np.array([np.cos(y + np.pi / 2), np.sin(y + np.pi / 2), 0.0])
    up = np.cross(fwd, right)  # Unreal is left-handed; checked by overlay
    d = Vw - np.array([cam["x"], cam["y"], cam["z"]])
    zc, xc, yc = d @ fwd, d @ right, d @ up
    f = (W / 2) / np.tan(np.radians(fov_deg) / 2)
    return np.stack([W / 2 + f * xc / zc, H / 2 - f * yc / zc], 1), zc


def front_vertex(uv, depth, pts, radius=3.0):
    """For each 2D point, the nearest-to-camera head vertex projecting within `radius` px."""
    idx = []
    for q in pts:
        d2 = ((uv - q) ** 2).sum(1)
        near = np.where(d2 < radius ** 2)[0]
        if len(near) == 0:
            near = np.argsort(d2)[:8]
        idx.append(int(near[np.argmin(depth[near])]))
    return np.array(idx)


def similarity(A, B):
    """Least-squares similarity transform mapping A (n x 2) onto B. Returns s, R, t."""
    ma, mb = A.mean(0), B.mean(0)
    a, b = A - ma, B - mb
    u, _, vt = np.linalg.svd(a.T @ b)
    R = u @ vt
    if np.linalg.det(R) < 0:
        u[:, -1] *= -1
        R = u @ vt
    s = np.trace((a @ R).T @ b) / (a ** 2).sum()
    return s, R, mb - s * ma @ R


def tps_fit(src, dst, smooth):
    """Thin-plate spline in 2D from src to dst points (cm). `smooth` regularises (cm^2)."""
    n = len(src)
    r2 = ((src[:, None] - src[None]) ** 2).sum(-1)
    K = np.where(r2 > 0, r2 * np.log(r2 + 1e-12), 0.0) + smooth * np.eye(n)
    P = np.hstack([np.ones((n, 1)), src])
    A = np.zeros((n + 3, n + 3))
    A[:n, :n], A[:n, n:], A[n:, :n] = K, P, P.T
    rhs = np.zeros((n + 3, 2))
    rhs[:n] = dst - src
    return src, np.linalg.solve(A, rhs)


def tps_eval(model, X):
    src, c = model
    n = len(src)
    r2 = ((X[:, None] - src[None]) ** 2).sum(-1)
    U = np.where(r2 > 0, r2 * np.log(r2 + 1e-12), 0.0)
    return U @ c[:n] + c[n] + X @ c[n + 1:]
