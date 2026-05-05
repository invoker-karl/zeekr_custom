# Zeekr App APK 3D Model Notes

APK inspected:

```text
D:/ruanjian/wechart/documents/xwechat_files/wuwan0505_c8ac/msg/file/2026-05/base.apk
```

The APK contains a Laya/Unity-style manifest for vehicle 3D resources:

```text
assets/hybrid/laya3DManifest.json
```

The Zeekr 7X entries are:

```text
bunId: 7X
targetPath: resources/car/7X
apk path: assets/hybrid/20250010077X3.zip
url: https://zeekrlife-oss.zeekrlife.com/frontend/unity/laya/hybrid/public/resources/car/7X/20250010077X3.zip
md5: 7bded1e1242db9822949f157477582c7
enMd5: 1cf05eb24c0b0759d4b7c2977424e0b1

bunId: 7X26
targetPath: resources/car/7X26
apk path: assets/hybrid/20250010077X263.zip
url: https://zeekrlife-oss.zeekrlife.com/frontend/unity/laya/hybrid/public/resources/car/7X26/20250010077X263.zip
md5: 9100e7970c0c93ee5a23ea7c45e78ecc
enMd5: 3816e36f60d02476869e23c92d352e42
```

Important finding:

The resource files inside the APK are not normal zip archives even though their
filenames end in `.zip`. Their file headers are high-entropy binary data, no
`PK` zip signature was found in the first megabyte, and Python `zipfile` rejects
them as `BadZipFile`.

For the 7X bundle:

```text
assets/hybrid/20250010077X3.zip
size: 12432784 bytes
raw md5: 1cf05eb24c0b0759d4b7c2977424e0b1
manifest enMd5: 1cf05eb24c0b0759d4b7c2977424e0b1
manifest md5: 7bded1e1242db9822949f157477582c7
```

The raw APK file matches `enMd5`, not `md5`, which strongly indicates the APK
stores the encrypted form of the Laya resource bundle. Without the app's normal
runtime decryption path or an already decrypted local cache, this project should
not attempt to bypass the encryption.

The public manifest URL was also checked with an HTTP range request. The first
64 bytes downloaded from:

```text
https://zeekrlife-oss.zeekrlife.com/frontend/unity/laya/hybrid/public/resources/car/7X/20250010077X3.zip
```

exactly match the first 64 bytes of the APK asset:

```text
f4bdf356c2fc81f2929ce284d1a0968ab8bdc95c90b4259d453fe57af8c319e4e259165ac94e060ae59c39cbe89e3f5a1b149b76a4fe51c6cf88dcb52bc63f77
```

So the online bundle is the same encrypted resource, not an alternate plaintext
zip or GLB.

Current project approach:

```text
www/zeekr_7x/model/index.html
```

now uses strict original-model mode. It does not render an approximate or
procedural car model. It only loads a legally obtained local original model
placed at:

```text
/config/www/zeekr_7x/model/zeekr_7x.glb
```

or:

```text
/config/www/zeekr_7x/model/zeekr_7x.gltf
```

State labels continue to work. If the GLB has named movable nodes, the page can
be extended to bind API state to those nodes.

Copyright note:

Official Zeekr app assets are proprietary. If a decrypted model is obtained from
the user's own phone/cache, keep it for personal local Home Assistant use and do
not redistribute it with this repository.
