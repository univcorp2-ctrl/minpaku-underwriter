const json = (body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });

export async function onRequestPost(context) {
  let body;
  try {
    body = await context.request.json();
  } catch {
    return json({ error: "invalid_json" }, 400);
  }
  const address = String(body.address || "").trim();
  if (!address) return json({ error: "address_required" }, 400);

  const headers = { "User-Agent": "minpaku-underwriter/1.0" };

  // Japan-first: GSI's address search handles Japanese block/house notation far
  // better than global geocoders for the addresses this product underwrites.
  try {
    const gsi = new URL("https://msearch.gsi.go.jp/address-search/AddressSearch");
    gsi.searchParams.set("q", address);
    const response = await fetch(gsi.toString(), { headers });
    if (response.ok) {
      const data = await response.json();
      const feature = Array.isArray(data) ? data[0] : null;
      if (feature?.geometry?.coordinates?.length >= 2) {
        const [lon, lat] = feature.geometry.coordinates;
        return json({
          lat: Number(lat),
          lon: Number(lon),
          provider: "gsi",
          matched_address: feature.properties?.title || null,
        });
      }
    }
  } catch {}

  try {
    const photon = new URL("https://photon.komoot.io/api/");
    photon.searchParams.set("q", address);
    photon.searchParams.set("limit", "1");
    const response = await fetch(photon.toString(), { headers });
    if (response.ok) {
      const data = await response.json();
      const feature = data.features && data.features[0];
      if (feature) {
        const [lon, lat] = feature.geometry.coordinates;
        return json({ lat, lon, provider: "photon" });
      }
    }
  } catch {}

  try {
    const nominatim = new URL("https://nominatim.openstreetmap.org/search");
    nominatim.searchParams.set("q", address);
    nominatim.searchParams.set("format", "jsonv2");
    nominatim.searchParams.set("limit", "1");
    const response = await fetch(nominatim.toString(), { headers });
    if (response.ok) {
      const data = await response.json();
      if (data[0]) {
        return json({
          lat: Number(data[0].lat),
          lon: Number(data[0].lon),
          provider: "nominatim",
        });
      }
    }
  } catch {}
  return json({ error: "geocode_not_found" }, 404);
}
