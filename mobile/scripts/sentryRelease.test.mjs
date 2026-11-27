import assert from 'node:assert/strict';
import test from 'node:test';
import { sentryReleaseEnvironment } from './sentryRelease.mjs';
import { buildEasEnvironment } from './release-build-plan.mjs';

test('the production API target cannot use an EAS profile name as its Sentry environment',()=>{
 const config={EXPO_PUBLIC_SENTRY_DSN:'https://public@example.invalid/1',EAS_BUILD_GIT_COMMIT_HASH:'a'.repeat(40),SENTRY_AUTH_TOKEN:'private-fixture',SENTRY_ORG:'fitician',SENTRY_PROJECT:'fitician-mobile',EXPO_PUBLIC_API_BASE_URL:'https://fitician.fit',EXPO_PUBLIC_SENTRY_ENVIRONMENT:'production'};
 assert.throws(()=>sentryReleaseEnvironment(config),/mobile_diagnostics_environment_mismatch/);
 assert.throws(()=>buildEasEnvironment({...config,EXPO_TOKEN:'synthetic'},'android'),/mobile_diagnostics_environment_mismatch/);
 assert.equal(sentryReleaseEnvironment({...config,EXPO_PUBLIC_SENTRY_ENVIRONMENT:'production-iran'}).SENTRY_RELEASE,'fitician-mobile@'+'a'.repeat(40));
 assert.throws(()=>sentryReleaseEnvironment({...config,EXPO_PUBLIC_API_BASE_URL:'https://fitician.fit/'}),/mobile_diagnostics_environment_mismatch/);
});

test('configured mobile capture requires an explicit environment even before a native build',()=>{
 assert.throws(()=>buildEasEnvironment({EXPO_TOKEN:'synthetic',EXPO_PUBLIC_SENTRY_DSN:'https://public@example.invalid/1'},'android'),/explicit_mobile_diagnostics_environment_required/);
});

test('production profiles without an API override still enforce the canonical backend environment',()=>{
 const config={EXPO_TOKEN:'synthetic',EXPO_PUBLIC_SENTRY_DSN:'https://public@example.invalid/1',EXPO_PUBLIC_SENTRY_ENVIRONMENT:'production'};
 assert.throws(()=>buildEasEnvironment({...config,EAS_BUILD_PROFILE:'production-device'},'android'),/mobile_diagnostics_environment_mismatch/);
});
test('configured native artifacts and runtime use the exact EAS commit',()=>{
 const sha='a'.repeat(40);
 assert.deepEqual(sentryReleaseEnvironment({EXPO_PUBLIC_SENTRY_DSN:'https://public@example.invalid/1',EXPO_PUBLIC_SENTRY_ENVIRONMENT:'staging',EAS_BUILD_GIT_COMMIT_HASH:sha,SENTRY_AUTH_TOKEN:'private-fixture',SENTRY_ORG:'fitician',SENTRY_PROJECT:'fitician-mobile'}),{SENTRY_RELEASE:'fitician-mobile@'+sha,EXPO_PUBLIC_APP_BUILD_SHA:sha});
});
test('an unknown or conflicting release cannot upload mismatched native artifacts',()=>{
 const config={EXPO_PUBLIC_SENTRY_DSN:'https://public@example.invalid/1',SENTRY_AUTH_TOKEN:'private-fixture',SENTRY_ORG:'fitician',SENTRY_PROJECT:'fitician-mobile'};
 assert.throws(()=>sentryReleaseEnvironment(config),/exact_mobile_release_commit_required/);
 assert.throws(()=>sentryReleaseEnvironment({...config,EAS_BUILD_GIT_COMMIT_HASH:'a'.repeat(40),EXPO_PUBLIC_APP_BUILD_SHA:'b'.repeat(40)}),/mobile_release_commit_mismatch/);
});
test('unconfigured builds remain independent from Sentry credentials',()=>{
 assert.deepEqual(sentryReleaseEnvironment({}),{SENTRY_DISABLE_AUTO_UPLOAD:'1'});
});
