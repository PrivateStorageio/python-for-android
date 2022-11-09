from pythonforandroid.recipe import CythonRecipe, IncludedFilesBehaviour
from pythonforandroid.util import current_directory
from pythonforandroid import logger

from os.path import join
from os import chmod, stat
from os import walk

def fix_perm(path):
    chmod(path, stat(path).st_mode | 0o200)

def fix_perms(root):
    logger.info(f'fixing perms on tree at {root}')
    fix_perm(root)
    for dirpath, dirnames, filenames in walk(root):
        for fname in dirnames + filenames:
            fix_perm(join(dirpath, fname))

class AndroidRecipe(IncludedFilesBehaviour, CythonRecipe):
    # name = 'android'
    version = None
    url = None

    src_filename = 'src'

    depends = [('sdl2', 'genericndkbuild'), 'pyjnius']

    config_env = {}

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env.update(self.config_env)
        return env

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        ctx_bootstrap = self.ctx.bootstrap.name

        # define macros for Cython, C, Python
        tpxi = 'DEF {} = {}\n'
        th = '#define {} {}\n'
        tpy = '{} = {}\n'

        # make sure bootstrap name is in unicode
        if isinstance(ctx_bootstrap, bytes):
            ctx_bootstrap = ctx_bootstrap.decode('utf-8')
        bootstrap = bootstrap_name = ctx_bootstrap
        is_sdl2 = (bootstrap_name == "sdl2")
        if bootstrap_name in ["sdl2", "webview", "service_only", "service_library"]:
            java_ns = u'org.kivy.android'
            jni_ns = u'org/kivy/android'
        else:
            logger.error((
                'unsupported bootstrap for android recipe: {}'
                ''.format(bootstrap_name)
            ))
            exit(1)

        config = {
            'BOOTSTRAP': bootstrap,
            'IS_SDL2': int(is_sdl2),
            'PY2': 0,
            'JAVA_NAMESPACE': java_ns,
            'JNI_NAMESPACE': jni_ns,
            'ACTIVITY_CLASS_NAME': self.ctx.activity_class_name,
            'ACTIVITY_CLASS_NAMESPACE': self.ctx.activity_class_name.replace('.', '/'),
            'SERVICE_CLASS_NAME': self.ctx.service_class_name,
        }

        # create config files for Cython, C and Python
        build_dir = self.get_build_dir(arch.arch)
        fix_perms(build_dir)
        with (
                current_directory(build_dir)), (
                open(join('android', 'config.pxi'), 'w')) as fpxi, (
                open(join('android', 'config.h'), 'w')) as fh, (
                open(join('android', 'config.py'), 'w')) as fpy:

            for key, value in config.items():
                fpxi.write(tpxi.format(key, repr(value)))
                fpy.write(tpy.format(key, repr(value)))

                fh.write(th.format(
                    key,
                    value if isinstance(value, int) else '"{}"'.format(value)
                ))
                self.config_env[key] = str(value)

            if is_sdl2:
                fh.write('JNIEnv *SDL_AndroidGetJNIEnv(void);\n')
                fh.write(
                    '#define SDL_ANDROID_GetJNIEnv SDL_AndroidGetJNIEnv\n'
                )
            else:
                fh.write('JNIEnv *WebView_AndroidGetJNIEnv(void);\n')
                fh.write(
                    '#define SDL_ANDROID_GetJNIEnv WebView_AndroidGetJNIEnv\n'
                )


recipe = AndroidRecipe()
