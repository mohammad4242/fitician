import assert from 'node:assert/strict';
import test from 'node:test';
import { sentryReleaseEnvironment } from './sentryRelease.mjs';
test('configured native artifacts and runtime use the exact EAS commit',()=>{
 const sha='a'.repeat(40);
 assert.deepEqual(sentryReleaseEnvironment({EXPO_PUBLIC_SENTRY_DSN:'https://public@example.invalid/1',EAS_BUILD_GIT_COMMIT_HASH:sha,SENTRY_AUTH_TOKEN:'private-fixture',SENTRY_ORG:'fitician',SENTRY_PROJECT:'fitician-mobile'}),{SENTRY_RELEASE:'fitician-mobile@'+sha,EXPO_PUBLIC_APP_BUILD_SHA:sha});
});
test('an unknown or conflicting release cannot upload mismatched native artifacts',()=>{
 const config={EXPO_PUBLIC_SENTRY_DSN:'https://public@example.invalid/1',SENTRY_AUTH_TOKEN:'private-fixture',SENTRY_ORG:'fitician',SENTRY_PROJECT:'fitician-mobile'};
 assert.throws(()=>sentryReleaseEnvironment(config),/exact_mobile_release_commit_required/);
 assert.throws(()=>sentryReleaseEnvironment({...config,EAS_BUILD_GIT_COMMIT_HASH:'a'.repeat(40),EXPO_PUBLIC_APP_BUILD_SHA:'b'.repeat(40)}),/mobile_release_commit_mismatch/);
});
test('unconfigured builds remain independent from Sentry credentials',()=>{
 assert.deepEqual(sentryReleaseEnvironment({}),{SENTRY_DISABLE_AUTO_UPLOAD:'1'});
});
