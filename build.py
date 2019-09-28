from distutils.extension import Extension


cmdclass = {}

try:
    # with Cython
    from Cython.Build import build_ext
    cmdclass["build_ext"] = build_ext
    module_src = "cgranges/python/cgranges.pyx"
except ImportError:  # without Cython
    module_src = "cgranges/python/cgranges.c"


def build(setup_kwargs):
    """
    This function is mandatory in order to build the extensions.
    """
    setup_kwargs.update(
        {
            "ext_modules": [
                Extension(
                    "cgranges",
                    sources=[module_src, "cgranges/cgranges.c"],
                    depends=[
                        "cgranges/cgranges.h",
                        "cgranges/khash.h",
                        "cgranges/python/cgranges.pyx"
                    ],
                    include_dirs=["cgranges"]
                )
            ],
            "cmdclass": cmdclass
        }
    )
