# Zorqi update test folder

This folder is a staging note for testing GitHub release updates. It contains no application patch and does not change/fix Zorqi by itself.

The Update Center reads published releases from `Oma100-tech/Zorqi-Shell`, looks for the `Zorqi-Setup.exe` release asset, downloads it, and opens the normal setup wizard. It does not apply files from this folder.

## Test a release update

1. Commit and push the desired app version to the `Oma100-tech/Zorqi-Shell` repository. The tagged build workflow must be present in that repository.
2. Update the app's displayed version before tagging a release so Update Center can tell when the installed version is current.
3. Push a version tag such as `v0.2.1`:

   ```powershell
   git tag v0.2.1
   git push https://github.com/Oma100-tech/Zorqi-Shell.git v0.2.1
   ```

4. The `Build Zorqi apps` workflow builds all platforms and publishes `Zorqi-Setup.exe` to the GitHub release for that tag.
5. Open **Zorqi Update Center** and choose **Check for updates**, then download and run the published installer.

For a no-code-change test, use a test tag only if you are comfortable creating a public GitHub release. This test folder alone does not create a release or upload an installer.
