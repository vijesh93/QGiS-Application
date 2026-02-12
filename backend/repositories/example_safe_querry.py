# validate layer name first with layer_repo.get_by_name(...)
# then build query safely — DO NOT interpolate unvalidated table names
# instead use a whitelist from layer_metadata.name
# Example (conceptual; requires careful parameterization):

def get_features_geojson(session, table_name, bbox=None, limit=100):
    # assume table_name has already been validated/whitelisted
    bbox_where = ""
    params = {"limit": limit}
    if bbox:
        bbox_where = "WHERE geom && ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 4326)"
        params.update({"xmin":bbox[0], "ymin":bbox[1], "xmax":bbox[2], "ymax":bbox[3]})
    sql = f"""
      SELECT json_build_object(
        'type','FeatureCollection',
        'features', json_agg(feature)
      ) FROM (
        SELECT json_build_object(
          'type', 'Feature',
          'id', id,
          'geometry', ST_AsGeoJSON(geom)::json,
          'properties', to_jsonb(t) - 'geom'
        ) AS feature
        FROM {table_name} t
        {bbox_where}
        LIMIT :limit
      ) s;
    """
    return session.exec(sql, params).one()