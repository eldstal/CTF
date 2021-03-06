import logging
import traceback

# A pseudo-backend which just tries to pick one of the real ones properly.
# Any backend with a static supports(conf, url) method can return True to claim support

# Pseudo-constructor
# Will construct one of the real Backends and return it
# If none is found, will print and return None
def SelectBackend(conf, middle):

    from backend import BACKENDS

    log = logging.getLogger(__name__)

    if len(conf["url"]) < 1:
        log.error(f"Backend autodetection requires a URL. Try --url or specify a backend using --backend")
        return None

    for name,implementation in BACKENDS.items():
        # Can only work with classes. There's a function pointer to auto in there.
        if type(implementation) != type:
            continue

        try:
            if implementation.supports(conf, conf["url"]):
                # It's a hit!
                log.info(f"Autodetection found backend {name}.")
                return implementation(conf, middle)
        except Exception as e:
            log.exception("Backend initialization failed.")

    log.error(f"Autodetection found no suitable backend. Try specifying with --backend.")
    return None

