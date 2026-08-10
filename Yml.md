name: App build on: push

jobs: build_with_signing: runs-on: macos-latest

```
steps:
  - name: Checkout repository
    uses: actions/checkout@v6
  - name: Install the Apple certificate and provisioning profile
    env:
      BUILD_CERTIFICATE_BASE64: ${{ secrets.BUILD_CERTIFICATE_BASE64 }}
      P12_PASSWORD: ${{ secrets.P12_PASSWORD }}
      BUILD_PROVISION_PROFILE_BASE64: ${{ secrets.BUILD_PROVISION_PROFILE_BASE64 }}
      KEYCHAIN_PASSWORD: ${{ secrets.KEYCHAIN_PASSWORD }}
    run: |
      # create variables
      CERTIFICATE_PATH=$RUNNER_TEMP/build_certificate.p12
      PP_PATH=$RUNNER_TEMP/build_pp.mobileprovision
      KEYCHAIN_PATH=$RUNNER_TEMP/app-signing.keychain-db

      # import certificate and provisioning profile from secrets
      echo -n "$BUILD_CERTIFICATE_BASE64" | base64 --decode -o $CERTIFICATE_PATH
      echo -n "$BUILD_PROVISION_PROFILE_BASE64" | base64 --decode -o $PP_PATH

      # create temporary keychain
      security create-keychain -p "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
      security set-keychain-settings -lut 21600 $KEYCHAIN_PATH
      security unlock-keychain -p "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH

      # import certificate to keychain
      security import $CERTIFICATE_PATH -P "$P12_PASSWORD" -A -t cert -f pkcs12 -k $KEYCHAIN_PATH
      security set-key-partition-list -S apple-tool:,apple: -k "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
      security list-keychain -d user -s $KEYCHAIN_PATH

      # apply provisioning profile
      mkdir -p ~/Library/MobileDevice/Provisioning\ Profiles
      cp $PP_PATH ~/Library/MobileDevice/Provisioning\ Profiles
  - name: Build app
      # ...
```
