# -*- mode: python -*-

block_cipher = None


a = Analysis(['aliexpress_products_crawler.py'],
             pathex=['/Users/ti/Working/Python/aliexpress_products_crawler'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='aliexpress_products_crawler',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False )
app = BUNDLE(exe,
             name='aliexpress_products_crawler.app',
             icon=None,
             bundle_identifier=None)
