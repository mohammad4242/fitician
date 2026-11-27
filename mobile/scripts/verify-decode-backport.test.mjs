import assert from 'node:assert/strict';
import test from 'node:test';
import {createRequire} from 'node:module';
import {performance} from 'node:perf_hooks';
const require=createRequire(import.meta.url);
const decode=require('decode-uri-component');

test('patched decoder preserves CommonJS query-string and Persian URL compatibility',()=>{
 assert.equal(decode('%D8%B3%D9%84%D8%A7%D9%85'),'سلام');
 const query=require('query-string');
 assert.equal(query.parse('name=%D8%B3%D9%84%D8%A7%D9%85').name,'سلام');
 assert.equal(decode('%E0%A4%A'),' %E0%A4%A'.trim());
});
test('malformed percent runs finish within a bounded budget without recursive amplification',()=>{
 const input=('%FF%41'.repeat(20000));const start=performance.now();
 assert.equal(decode(input),'%FFA'.repeat(20000));
 assert.ok(performance.now()-start<2000,'Malformed URL decoder exceeded the test budget');
});
