/**
 * Serves identity-engineering.org/releases/ie-os/* from R2 bucket ie-os-releases.
 * Object key = URL path without leading slash.
 * e.g. /releases/ie-os/0.1.0/ie_os-0.1.0.tar.gz -> releases/ie-os/0.1.0/ie_os-0.1.0.tar.gz
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (!url.pathname.startsWith("/releases/ie-os/")) {
      return new Response("Not Found", { status: 404 });
    }

    const key = url.pathname.slice(1);
    const object = await env.IE_OS_RELEASES.get(key);

    if (!object) {
      return new Response("Not Found", { status: 404 });
    }

    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set("etag", object.httpEtag);
    headers.set("cache-control", "public, max-age=31536000, immutable");

    return new Response(object.body, { headers });
  },
};
