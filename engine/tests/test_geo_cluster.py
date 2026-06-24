from utils.geo_cluster import cluster_centroid, cluster_points, infer_place_type


def test_cluster_dominant_place():
    # two clusters: 5 points near (34.62, 112.45), 2 points far away
    near = [(34.620 + i * 0.0001, 112.450 + i * 0.0001) for i in range(8)]
    far = [(34.70, 112.50), (34.701, 112.501)]
    clusters = cluster_points(near + far)
    assert len(clusters) >= 2
    assert len(clusters[0]) >= 8
    lat, lon = cluster_centroid(clusters[0])
    assert abs(lat - 34.62) < 0.01
    assert infer_place_type(clusters, len(near) + len(far)) == "routine"
