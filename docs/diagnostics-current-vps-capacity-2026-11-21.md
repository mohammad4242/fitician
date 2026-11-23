# ارزیابی ظرفیت diagnostics روی VPSهای فعلی — 2026-11-21

## کنترل تازه — 22 نوامبر، 05:28 UTC

مسیر API مدل اکنون کامل به آلمان منتقل شده و policy حالت shared برای scheduler موجود
پیاده‌سازی و تست شده است. هیچ تنظیم production اعمال نشده است. کلید اختصاصی هنوز آماده نیست.
نمونهٔ تازه: RAM قابل‌استفاده ایران1493 و آلمان1305 MiB، دیسک آزاد ایران9872 و آلمان2449 MiB؛
CPU به‌ترتیب2 و1، load یک‌دقیقه‌ای1.09 و0.13. این snapshot جایگزین اندازه‌گیری peak نیست.
همهٔ سرویس‌های فعال دارای healthcheck سالم بودند؛ کانتینرهای خاموش rehearsal محاسبه نمی‌شوند.
DB ایران175 و30 اتصال مشاهده شد. runtime آلمان هنوز `awaiting_enrollment` است.

scheduler فعلی153.8 از192 MiB working set دارد؛ حاشیهٔ فعلی38.2 MiB از gate محافظه‌کارانه64
کمتر است. gate جدید علاوه بر750 MiB ذخیرهٔ میزبان،256 MiB عدم‌قطعیت و64 MiB حاشیه داخل
scheduler می‌خواهد؛ consumption واقعی cgroup در preflight دوباره خوانده می‌شود. تخصیص256
در آزمون جداگانهٔ قبلی استفاده شد؛ تغییر این سقف در production هنوز مجوز ندارد.
وجود1493 MiB RAM آزاد اثبات نمی‌کند همهٔ بارهای اوج پاس شده‌اند، اما ضرورت ارتقای VPS را
هم ثابت نمی‌کند. آلمان همچنان کمتر از guard دیسک3 GiB دارد؛ هیچ فایل یا image حذف نشد.

## به‌روزرسانی اجرایی — 22 نوامبر تهران / 21 نوامبر UTC

پس از گزارش اولیه، batching و شمارنده‌های افت writer، housekeeping زمان‌بندی‌شده،
رفع توقف event loop در readiness، App Server پایدارِ سریالی و dispatch سبک Codex
در scheduler پیاده‌سازی شدند. دو نقش sync/SMS نیز می‌توانند در scheduler اجرا شوند.
همهٔ flagها پیش‌فرض خاموش‌اند؛ تنظیم تولید تغییر نکرده است. انتقال حلقهٔ مدل API
به آلمان و اتصال این حالت مشترک به release-policy هنوز کامل نیست.

### نمونه‌برداری تازه و هم‌زمانی

61 نمونه، `19:50:15–19:55:16 UTC`؛ فایل‌های اصلی در مسیر ignored
`.codex-tmp/completion-20261121/` هستند. مقادیر حداقل و حداکثر بی‌ارتباط جمع نشده‌اند.

| شاخص | ایران | آلمان |
| --- | ---: | ---: |
| CPU / RAM فیزیکی MiB | 2 / 3916 | 1 / 1968 |
| کمترین MemAvailable، MiB | 1462.8 | 1329.6 |
| میانگین / p95 / بیشینه CPU میزبان | 10.59 / 17.67 / 18.89% | 8.75 / 15.83 / 19.88% |
| بیشینه WS هم‌زمان Docker، MiB | 1579.4 | 276.2 |
| MemAvailable در همان قلهٔ Docker، MiB | 1471.5 | 1339.7 |
| زمان قلهٔ Docker، UTC | 19:51:50 | 19:55:01 |
| مجموع سقف‌های فعلی Docker، MiB | 2880 | 1152 |
| بیشینه swap مصرف‌شده، MiB | 757.2 | 47.6 |
| دیسک قابل‌استفادهٔ غیررزروشده، MiB | 9821.9 | 2318.4 |
| OOM / restart جدید | 0 / 0 | 0 / 0 |

در بررسی بعدی `21:38 UTC`، available RAM ایران 1466 و آلمان 1318 MiB بود؛
هویت و زمان شروع 10 سرویس ایران و 4 سرویس آلمان تغییر نکرده بود. در کنترل نهایی
`22:28 UTC` نیز همین هویت‌ها، DB175 و RAM آزاد1491/1321 MiB ثبت شد. revision واقعی
DB دوباره `20261018_175` و connection count برابر 30 خوانده شد. سقف DB برابر100
و Redis در نمونهٔ ده‌ثانیه‌ای حدود1.02 MiB، peak حدود3.69 MiB از128 MiB بود.
رشد log کانتینرها طی ده ثانیه ایران1217 و آلمان450 بایت بود؛ این نرخ کوتاه،
پیش‌بینی رشد ماهانه نیست. ترافیک host آلمان شامل غیر Fitician هم هست.

| سرویس ایران | سقف MiB | میانگین / بیشینه WS MiB |
| --- | ---: | ---: |
| backend | 512 | 395.5 / 406.3 |
| backend-2 | 512 | 358.9 / 371.8 |
| PostgreSQL | 512 | 192.7 / 193.0 |
| Redis | 192 | 2.1 / 2.2 |
| body-analysis-worker | 384 | 59.3 / 59.3 |
| food-photo-worker | 256 | 184.3 / 184.3 |
| scheduler | 192 | 153.8 / 154.2 |
| notification-worker | 192 | 182.4 / 183.9 |
| frontend / caddy | 64 / 64 | 6.1 / 20.9 |

| سرویس آلمان | سقف MiB | میانگین / بیشینه WS MiB |
| --- | ---: | ---: |
| connector، شامل Codex در همان cgroup | 512 | 147.3 / 164.4 |
| generation agent-service جدا | 448 | 65.0 / 68.6 |
| proxy | 96 | 24.4 / 28.2 |
| install-site | 96 | 22.5 / 22.5 |
| automation broker | پیشنهادی192 | هنوز اجرا نشده؛ اندازه‌گیری نشده |

این پنجرهٔ آلمان عمدتاً idle/awaiting_enrollment است؛ اندازهٔ Codex تحت بار مدل
و هم‌زمان با generation را ثابت نمی‌کند. محدودیت512 MiB شامل فرزند App Server
است؛ آن را یک سرویس512 MiB دیگر جمع نمی‌کنیم.

### نتیجهٔ آزمایش اصلاح‌شده

روی source `21e647e9`، دو CPU مشترک و ده سرویس با سقف‌های متناظر؛ scheduler فقط
در محیط جدا256 MiB، Redis AOF روشن، صف diagnostics همان256 و sampling بدون کاهش:

- 600 درخواست با10 RPS: همه200، p95 برابر530 ms، p99 برابر757 ms؛ 13246 مشاهده
  تأییدشده و افت جدید صفر.
- سه burst سیصددرخواستی با concurrencyهای5/10/20: همه200 و timeout صفر؛
  p95 برابر861/1310/1848 ms، بالاتر از هدف750 ms؛ gate تأخیر burst پاس نیست.
- پس از burst، 971 مشاهدهٔ کم‌اولویت به‌صورت صریح رد شدند؛ persistence failure،
  OOM و restart صفر. buffer محدود است و abrupt process loss همچنان شواهد نامعلوم دارد.
- بیشینه WS هم‌زمان در بار پایدار حدود1558 MiB بود. DB روی tmpfs و CPU لپ‌تاپ
  متفاوت بود؛ این آزمایش جای بار واقعی VPS، disk I/O و مدل واقعی را نمی‌گیرد.

علت توقف HTTP قبلی صرفاً کمبود RAM نبود: probe readiness روی event loop منتظر
connection pool می‌ماند. این مسیر اکنون به thread pool موجود منتقل شده؛ سقف یا
timeout DB افزایش نیافته است. 30 job قبلی صف‌شده با provider مصنوعی به
review_pending رسیدند؛ این عبارت به‌معنای اجرای هم‌زمان30 مدل واقعی نیست.

### دیسک و بودجهٔ فعال‌سازی

بررسی read-only در `21:55 UTC`: ایران تصاویر7.831 GB و volumeها917.6 MB؛ آلمان
تصاویر7.037 GB و volumeها711.5 MB. اندازهٔ هر image شامل layer مشترک است و نباید
برای مصرف واقعی دیسک جمع شود. عبارت reclaimable مجوز حذف imageِ rollback نیست.
روی آلمان حداقل حدود1.02 GiB بلوک رزروشدهٔ filesystem وجود دارد؛ آن را فضای آزاد
قابل‌مصرف runtime محسوب نکردیم.

32 journal آرشیوی حدود1512 MiB و journal فعال48 MiB هستند. بررسی نام/size/mtime
مشخص کرد vacuum تا256 MiB می‌تواند حدود1360 MiB از29 آرشیو قدیمی بازیابی کند؛
هیچ فایل حذف نشده است. دستور پیشنهادیِ نیازمند تأیید جداگانه:
`sudo journalctl --vacuum-size=256M`. این حذف log قدیمی برگشت‌پذیر نیست؛ ابتدا
آرشیو رمز‌شده و checksum در مقصد backup بررسی شود. auth state، volumeها و imageهای
قبلی دست‌نخورده می‌مانند. پس از هر cleanup باید guard واقعی artifact تازه اجرا شود؛
عدد بالقوهٔ بازیابی، مجوز استقرار یا اثبات کفایت همهٔ artifactها نیست.

بودجهٔ پیشنهادی ایران: همان سرویس‌ها، scheduler256، مجموع سقف2944 + ذخیره750 =
3694 MiB از3916؛ برای آلمان مجموع1344 + ذخیره384 =1728 MiB از1968. اینها
reservation محافظه‌کارانه‌اند، نه مصرف اندازه‌گیری‌شده. هیچ حد فعلی کم نشده است.
ارتقای پولی اجتناب‌ناپذیر اثبات نشده؛ deployment آلمان فعلاً به guard دیسک می‌خورد،
و پذیرش هم‌زمان مدل/تعمیر/کسب‌وکار و wiring انتشار هنوز باقی است.

## نتیجه و حدود اعتبار

**نیاز فنیِ اجتناب‌ناپذیر به ارتقای پولی ایران اثبات نشده است.** محاسبهٔ قبلیِ
4654 MiB مربوط به اجرای سه worker مستقلِ جدید در ایران بود؛ این محاسبه معادل مصرف
واقعی و الزام معماری نیست. با حفظ داده/صف در ایران، اجرای مدل/تعمیر در آلمان و
یکپارچه‌کردن کنترل‌های سبک با scheduler موجود، گزینهٔ بدون ارتقا ارزش ادامه دارد.
این یک پیشنهادِ مبتنی بر اندازه‌گیری و نمونهٔ آزمایشی است؛ پنل production هنوز با این
معماری تکمیل/منتشر/پذیرفته نشده است.

در این بررسی هیچ VPS خریداری/resize نشد، تنظیم یا سرویس production تغییر/ری‌استارت
نکرد، worker موجود متوقف نشد، پایگاه‌داده جابه‌جا نشد و SMS واقعی ارسال نشد.
سقف‌ها یا sampling تولید کاهش نیافتند. تغییرات محلی دیگر کاربر محفوظ ماندند.

## شواهد و روش اندازه‌گیری

- source آزمایش: `de626ca6a0daf67f38f738823258dc07158d8733`، branch
  `feat/regional-cicd`. منبع با `git archive HEAD backend` منجمد شد؛ فایل‌های محلی
  و secretهای checkout وارد image نشدند.
- image آزمایش:
  `sha256:db598c3638f8c3ae698dbe22c2e8cdb7c85c49ffe5f64bea3ba49eabe571aeb5`.
- هر میزبان: 61 نمونه با فاصلهٔ 5 ثانیه، حدود 300 ثانیه؛ ایران
  `15:22:11–15:27:12 UTC` و آلمان `15:22:13–15:27:13 UTC` در 21 نوامبر.
- خواندن read-only از `/proc`، cgroup و metadata محدودشدهٔ Docker؛ Env یا secret
  چاپ/ذخیره نشد. `working set = memory.current - inactive_file` است؛ سقف Docker
  مصرف محسوب نشده است.
- سوابق موجود sysstat: 143 نمونهٔ 20 نوامبر و 95 نمونهٔ 21 نوامبر تا حدود
  15:50؛ فاصلهٔ معمول 10 دقیقه. این حدود 40 ساعت سابقه است، نه ثبت همهٔ قله‌های
  لحظه‌ای یا تضمین بار آینده.
- `memory.peak` قلهٔ طول عمر cgroup و شامل cache/healthcheck/operator exec است؛
  قله‌های سرویس‌ها هم‌زمان فرض نشده‌اند. بیشینهٔ working set هم‌زمان جدا محاسبه شد.
- خروجی‌ها و ابزارهای آزمایش فقط در مسیر ignored
  `.codex-tmp/capacity-20261121/` نگهداری شدند؛ اطلاعات نشست fixture دسترسی 0600 دارد.

## وضعیت اندازه‌گیری‌شدهٔ میزبان‌ها

| شاخص | ایران | آلمان |
| --- | ---: | ---: |
| vCPU | 2 | 1 |
| RAM فیزیکی، MiB | 3916 | 1968 |
| کمترین MemAvailable در 5 دقیقه، MiB | 1438 | 1277 |
| کمترین MemAvailable در سابقه، MiB | 1346 | 1220 |
| میانگین CPU میزبان در 5 دقیقه | 11.26% | 10.27% |
| بیشینهٔ CPU میزبان در فاصلهٔ 5 ثانیه | 22.26% | 39.32% |
| بیشینهٔ میانگین CPU در فاصلهٔ تاریخی | 28.65% | 20.49% |
| بیشینهٔ working set هم‌زمان Docker، MiB | 1590 | 547 |
| مجموع سقف RAM کانتینرهای فعلی، MiB | 2880 | 1152 |
| بیشینهٔ swap مصرف‌شده در 5 دقیقه، MiB | 758 | 48 |
| دیسک آزاد در snapshot، MiB | 9825 | 2320 |

در پنجرهٔ جداگانهٔ یک‌دقیقه‌ای هر دو میزبان، افزایش swap-in/swap-out، major fault
و OOM صفر بود. بااین‌حال سوابق ایران تا 57.23 page/s swap-in و 94.56 page/s
swap-out نشان می‌دهد؛ پس مصرف swap را نه خرابی قطعی می‌دانیم و نه بی‌اهمیت.
بازگشت هم‌زمان همهٔ صفحات سرد به RAM آزمایش نشده است. در نمونه‌برداری زنده OOM
یا restart جدید ثبت نشد. notification-worker یک restart قدیمی داشت؛ علتش از این
داده معلوم نیست.

PostgreSQL: سقف 100 connection، 30 connection مشاهده‌شده شامل backgroundها، 22
client، یک active و 21 idle؛ idle-in-transaction صفر. اندازهٔ دیتابیس حدود 283 MiB
بود. هیچ سطر کاربر برای این ارزیابی خوانده نشد.

## تخصیص سرویس‌های ایران

همهٔ اعداد حافظه MiB هستند. «پیشنهادی» تنظیم اعمال‌شده نیست. CPU سقف برحسب core
و ستون آخر قلهٔ مصرف یک core در پنجرهٔ 5 دقیقه‌ای است.

| سرویس | سقف فعلی | میانگین WS | بیشینه WS | قلهٔ عمر cgroup | سقف پیشنهادی | CPU سقف / قلهٔ مصرف |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| backend | 512 | 395.8 | 416.8 | 512.0 | 512 | 0.40 / 10.16% |
| backend-2 | 512 | 359.4 | 381.8 | 444.8 | 512 | 0.40 / 13.19% |
| db | 512 | 205.3 | 205.9 | 512.0 | 512 | 0.35 / 3.47% |
| redis | 192 | 2.1 | 3.6 | 11.1 | 192 | 0.10 / 1.13% |
| body-analysis-worker | 384 | 59.5 | 72.2 | 364.3 | 384 | 0.35 / 8.43% |
| food-photo-worker | 256 | 184.5 | 197.1 | 256.0 | 256 | 0.20 / 9.52% |
| scheduler | 192 | 154.0 | 166.6 | 192.0 | 256 | 0.15 / 9.59% |
| notification-worker | 192 | 182.3 | 182.7 | 192.0 | 192 | 0.10 / 9.00% |
| frontend | 64 | 6.2 | 7.7 | 37.3 | 64 | 0.05 / 0.73% |
| caddy | 64 | 20.6 | 20.6 | 59.2 | 64 | 0.10 / 0.33% |

سقف notification-worker نزدیک مصرف فعلی است؛ کارهای جدید را بدون اندازه‌گیری به آن
اضافه نمی‌کنیم. scheduler در آزمایش مشترک با سقف 192 MiB به حدود 191 MiB رسید؛
پیشنهاد 256 MiB افزایش حاشیه است، نه کاهش محدودیت موجود. مقدار هیچ سرویس دیگری
در این پیشنهاد از مقدار زنده کمتر نمی‌شود. defaultهای `.env.example` و guard عمومی
با همهٔ overrideهای واقعی برابر نیستند؛ release باید از Compose نهایی renderشده و
مقادیر همین سرویس‌ها محاسبه شود، نه از defaultهای یک topology دیگر.

## تخصیص سرویس‌های آلمان

| سرویس | سقف فعلی | میانگین WS | بیشینه WS | قلهٔ عمر cgroup | سقف پیشنهادی | CPU سقف / قلهٔ مصرف |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| connector | 512 | 147.0 | 164.4 | 201.6 | 512 | 0.25 / 11.66% |
| agent-service | 448 | 144.6 | 340.8 | 448.9 | 448 | 0.40 / 29.92% |
| proxy | 96 | 24.8 | 28.7 | 40.6 | 96 | 0.25 / 1.49% |
| install-site | 96 | 22.4 | 22.5 | 57.4 | 96 | 0.20 / 0.65% |
| automation broker | اجرا نشده | — | — | — | 192 | 0.10 / اندازه‌گیری نشده |

connector فعلی همان commissioning service است؛ وجود آن اثبات اتصال پنل production
نیست. Codex و adapter مدل API باید در همین execution boundary توسعه یابند، نه در
یک runtime رقیب. generation Agent جدا باقی می‌ماند. CI شامل PostgreSQL integration،
frontend build و native build روی GitHub Actions انجام شود؛ آلمان محل اجرای هم‌زمان
buildهای سنگین نیست. یک run اجرایی فعال با workspace و صف محدود لازم است؛ laptop
فقط target اختیاری می‌ماند. بار هم‌زمان واقعی مدل debug و generation هنوز پذیرش نشده.

## چه چیزهایی واقعاً باید در ایران بمانند؟

**پیشنهاد: صفر سرویس standalone جدید در ایران، با کار مهندسیِ انجام‌نشدهٔ زیر.**

| مسئولیت | محل | علت/نحوه |
| --- | --- | --- |
| API، auth/admin، DB، Redis و صف‌های کسب‌وکار | ایران | مالکیت داده و معماری فعلی حفظ می‌شود |
| workerهای body/food، scheduler، notification | ایران | همان workerهای موجود؛ بدون duplicate |
| انتخاب occurrence، snapshot پاک‌سازی‌شده، claim/lease/finalization | ایران | تراکنش DB و مجوزها محلی می‌مانند |
| Sentry sync/discovery و health منطقی آن | ایران | نگاشت occurrence/دادهٔ محلی؛ fetch از egress موجود آلمان |
| تجمیع SMS، cooldown، claim و receipt | ایران | شماره/کلید Faraz و ثبت durable پیش از ارسال محلی می‌ماند |
| Codex، حلقهٔ مدل API، ابزار مخزن و تعمیر | آلمان | workload مدل/کد از API و صف تولید جدا می‌شود |
| GitHub Broker و CI orchestration | آلمان | credential محدود GitHub جدا؛ CI روی Actions |

سه ردیف کنترل سبک ایران می‌توانند به‌صورت loopهای محدودشده در scheduler موجود
جای گیرند، با heartbeat مستقل هر نقش، backoff، fairness و lease durable؛ خرابی یک
loop نباید heartbeat نقش دیگر را سالم جلوه دهد. thread/async scheduling باید بر اساس
I/O واقعی انتخاب و cancellation/restart آزموده شود. انتقال سادهٔ container فعلی
`debug-worker` به آلمان معتبر نیست: `execute_run` مستقیماً DB و کلید decrypt provider
را مصرف می‌کند و OpenRouter orchestration فعلاً در همین worker است.

برای انتقال واقعی حلقهٔ API باید قرارداد scoped claim/evidence/result و adapter ریموت
اضافه شود؛ config/model/options و target روی هر run ثابت بمانند. DB URL و کلید encryption
ایران به آلمان منتقل نشوند. credential مدل به credential store محدود runtime یا مسیر
محدودِ provider دسترسی پیدا کند؛ شیوهٔ نهایی credential نیازمند طراحی/بازبینی است و
در این بررسی بی‌صدا اعمال نشده. مدل فاقد tools همچنان analysis-only بماند.

مسیرهای قابل استناد: `backend/app/debugging/worker.py:86` و `:397`؛
`backend/app/debugging/connector_router.py:32`؛ `backend/app/scheduler/worker.py:59`؛
`backend/app/observability/sentry_sync.py:302`؛
`backend/app/observability/alert_worker.py:31`؛ `compose.debugging.yaml:4`، `:35`، `:68`؛
`compose.debug-runtime.yaml:4` و `:37`.

## بودجه و حاشیهٔ امن پیشنهادی

- ایران: سقف فعلی 2880 + افزایش آزمایشی scheduler به‌اندازهٔ 64 = **2944 MiB**؛
  با reserve موجود 750، جمع 3694 و حاشیهٔ رسمی حدود **222 MiB** است. CPU مجموع
  سقف‌ها همان **2.2 core** می‌ماند؛ oversubscription برابر مصرف هم‌زمان نیست.
- با تکیه بر کمترین MemAvailable تاریخی 1346 و بودجهٔ افزایشی محافظه‌کارانهٔ
  **128 MiB** برای control plane مشترک، برآورد مشروط 1218 MiB باقی می‌ماند؛
  حدود **468 MiB بالاتر از reserve 750**. این برآورد admission است، نه تضمین peak
  همهٔ صف‌ها، قیمت‌گذاری هفتگی، تصاویر بیشینه یا صفحات swapشده.
- migration موقت با سقف 256 MiB نیز باید جدا حساب شود: 2944+256+750=3950 که
  حدود 34 MiB از RAM فیزیکی بیشتر است. این جمع سقف به‌تنهایی upgrade را ثابت نمی‌کند،
  ولی guard/پنجرهٔ migration هنوز نیاز به rehearsal و برنامهٔ ظرفیت جدا دارد؛ reserve
  یا سقف‌ها نباید برای عبور ظاهری کاهش یابند. migration production مجاز/انجام‌شده نیست.
- آلمان با broker: **1344 MiB** مجموع سقف؛ با reserve guard برابر 384 جمع **1728**،
  حدود **240 MiB** حاشیهٔ رسمی دارد. CPU سقف مجموع **1.2 core** روی یک core است؛
  اجرای هم‌زمان مدل‌های واقعی هنوز باید جدا سنجیده شود.
- این اعداد جای guard فعلی را عوض نمی‌کنند. profile سه-worker ایران با سقف 1024 MiB
  اضافی همچنان رد می‌شود؛ معماری مشترک باید اول در code/health/release policy پیاده شود.

## آزمون‌های ایزوله و نتایج واقعی

project فقط آزمایشی `fitician-capacity-3d217420` با ده سرویس و network داخلی بود.
همهٔ سرویس‌ها روی **دو CPU یکسان 18,19** محدود شدند؛ load client روی دو CPU دیگر.
سقف RAM/CPU مطابق ایران بود؛ تنها در مرحلهٔ مشترک scheduler محلی از 192 به 256 رفت.
swap کانتینرهای آزمون خاموش بود. source اصلی app تغییر نکرد؛ wrapperهای آزمایشی فقط
bind شدند. هیچ secret/دادهٔ production یا provider واقعی وارد محیط نشد.

| آزمون | نتیجه |
| --- | --- |
| catalogue، 300 درخواست، concurrency=5 | 26.37 RPS، p95=566 ms، همه 200 |
| catalogue، concurrency=10 | 30.42 RPS، p95=887 ms، همه 200؛ SLO=750 ms رد شد |
| catalogue، concurrency=20 | 32.70 RPS، p95=1312 ms، همه 200؛ SLO رد شد |
| maintenance مشترک در scheduler با سقف 192 | بدون OOM؛ peak حدود 191 MiB، حاشیه ناکافی |
| maintenance با سقف 256، بار پایدار 1200 درخواست/120 ثانیه | 10 RPS، همه 200، p95=246 و p99=600 ms |
| هم‌زمان با آزمون 120ثانیه‌ای، 30 body job با provider ساختگی | همه review_pending؛ هر کدام دقیقاً یک result version |
| همان بازهٔ 120ثانیه‌ای | بیشینه WS هم‌زمان 1523 MiB؛ CPU میانگین 0.935 و max=1.093 core؛ بدون OOM |
| writer فعلی، 600 درخواست/60 ثانیه، 10 RPS | همه 200، p95=261 ms؛ **843 observation حذف شد** |
| نمونهٔ batch، همان 600 درخواست/10 RPS و سقف‌ها | همه 200؛ p95=495 و p99=720 ms؛ **افزایش drop صفر** |
| invariantهای نمونهٔ batch روی PostgreSQL | duplicate span UUID، شمارش issue و dedup event UUID پاس؛ rollback تراکنش |

### گلوگاه اندازه‌گیری‌شده، مستقل از خرید VPS

writer فعلی برای هر observation یک Session/commit انجام می‌دهد
(`backend/app/observability/diagnostics_runtime.py:493`). صف 256، sampling موفق 1.0
و سقف هر API برابر 0.4 core حفظ شدند. در آزمون دقیق 60ثانیه‌ای، counter دو API
533 و 310 افزایش یافت، بدون log خطای persistence در همان بازه. پس HTTP 200 به‌معنای
سلامت capture نبود. در آزمون 120ثانیه‌ای دو API در حدود 96% دوره‌ها throttle شدند،
درحالی‌که مصرف کل حدود نصف دو core بود. افزودن CPU میزبان به‌تنهایی quota یا writer
تک‌رویدادی را اصلاح نمی‌کند.

نمونهٔ batch فقط رکوردهای span را تا 32تایی با upsert UUID ثبت کرد؛ eventهای عادی
همچنان از `record_event` عبور کردند. sampling، queue و quota عوض نشدند. نتیجهٔ صفر
حذف، شاهد امکان بهبود نرم‌افزاری است، نه ادعای zero-loss یا اصلاح آمادهٔ production.
این نمونه در Git/source محصول نصب نشده و رفتار خطای batch/commit نامطمئن، حفظ اولویت
خطا، retry و restart هنوز باید برای تبدیل آن به محصول تست شوند. latency این نمونه
از baseline دقیقه‌ای بیشتر بود؛ آن را بهبود تضمینی latency معرفی نمی‌کنیم.
در 48 نمونهٔ منابع داخل بازهٔ batch، WS هم‌زمان حداکثر 1563 MiB و CPU میانگین
0.665/max=1.002 core بود؛ monitor کل 60 ثانیه را پوشش نداد، پس قلهٔ کامل این run معلوم نیست.

maintenance آزمایشی یک payload ساختگی Sentry حدود 1.64 MiB، حلقهٔ sync/discovery،
alert claim/receipt و claim صف debug خالی را کنار scheduler موجود اجرا کرد؛ آخرین
430 tick و 36 fetch با صفر خطا ثبت شد. یک receipt ساختگی provider_delivered بود و
سه alert fixture هنوز queued بودند. این **آزمون live Sentry/SMS یا اجرای واقعی مدل نیست**.

### محدودیت‌ها و آزمون‌های نامعتبر کنارگذاشته‌شده

- PostgreSQL روی tmpfs و Redis با AOF خاموش بود؛ بار catalogue عمدتاً read است.
  دوام/IO دیسک تولید، AOF rewrite و backup هم‌زمان با قلهٔ بار اثبات نشده‌اند.
- body provider ساختگی بود؛ decoding تصاویر بیشینه، inference واقعی، هم‌زمانی چهار
  workflow، بار هفتگی قیمت‌گذاری و concurrent debug/generation کامل آزموده نشدند.
- سخت‌افزار آزمایش laptop است، با affinity/quota؛ benchmark معادل VPS و SLA عمومی نیست.
  کلون کامل RAM میزبان نبود، اما همهٔ کانتینرها سقف واقعی و swap ممنوع داشتند.
- اولین probe با host-port شبکهٔ داخلی خروجی HTTP صفر داد و کنار گذاشته شد؛ client
  به network داخلی منتقل شد. یک run دیگر نشست منقضی و 1200 پاسخ 401 داشت؛ پس از
  ساخت نشست synthetic تازه، آزمون معتبر تکرار شد. این‌ها throughput موفق محسوب نشدند.
- چند خطای fixture اولیه (قالب Caddy، registry seed، state receipt و tmpfs تست)
  اصلاح شدند؛ هیچ‌کدام به تولید نسبت داده نشده‌اند. تست batch ابتدا import generic
  insert اشتباه داشت؛ با dialect PostgreSQL اصلاح و invariantها سپس پاس شدند.

## ارتباط خصوصی و مرز داده

برای هر پنج مصرف‌کنندهٔ واقعی ایران (دو API، scheduler، body و food worker)، DNS
خصوصی Agent به `100.108.24.126` رسید؛ GET `/healthz` و GET احراز‌شدهٔ
`/v1/capabilities` هر دو 200 بودند. TLS و host-key verification روشن ماندند.
از آلمان به `100.107.212.79:443` با SNI واقعی `fitician.fit`، health=200 و auth/me=401
دریافت شد؛ رد ناشناس مورد انتظار است. TCP مستقیم 5432/6379 از آلمان connection-refused
بود. این scoped HTTP path را نشان می‌دهد، نه اثبات همهٔ ACLهای tailnet.
probe اولیهٔ hostname نادرست کنار گذاشته و با دامنهٔ واقعی running Caddy تکرار شد.

در env keyهای allowlistشده و mountهای چهار سرویس آلمان DB/S3/Faraz/recipient credential
مشاهده نشد؛ audit، اسکن کامل همهٔ secretهای filesystem نیست. در این کار هیچ دادهٔ خصوصی
یا credential DB به آلمان منتقل نشد. مسیر debug باید فقط evidence پاک‌سازی‌شده، شناسهٔ
opaque، source code و وضعیت محدود دریافت کند؛ raw فرم/عکس/prompt/log خصوصی ممنوع بماند.

**استثنای معماریِ از قبل موجود:** مسیر business Agent برای body/food می‌تواند image bytes
را با multipart ارسال کند (`backend/app/body_analysis/providers/agent_service.py:283`).
بنابراین ادعای «هیچ دادهٔ کاربری در کل معماری هرگز به آلمان نمی‌رود» نادرست است.
این مسیر موجود تغییر نکرد و با دسترسی debug به عکس‌های کاربران یکی نیست. اگر هدف
ممنوعیت همهٔ ارسال عکس‌های کسب‌وکار به آلمان باشد، تصمیم جداگانه‌ای لازم است؛ در این
ارزیابی آن جریان موجود حذف یا جایگزین نشده است.

## دیسک آلمان: مانع واقعی انتشار، نه الزام خرید

آزاد حدود 2320 MiB است. guard در `ops/deploy-debug-runtime.py:357` حداقل
`max(3 GiB, unpacked image + 1.5 GiB)` می‌خواهد؛ فضای archive پیش از unpack هم
باید لحاظ شود. این gate فعلاً رد می‌شود. guard کاهش نیافت.

Docker حدود 1.58 GB قابل reclaim گزارش کرد؛ یک image قدیمی بدون container reference
هم یافت شد، اما ممکن است rollback artifact باشد و حجم آن الزاماً فضای آزادشدنیِ
منحصر نیست. journal حدود 1.3 GB، `/var/log` حدود 1.73 GB و apt cache حدود 152 MiB
بودند. هیچ prune/حذف/تغییر retention انجام نشد. قبل از هر خرید، review جداگانهٔ retention
و rollback-safe cleanup و سنجش دوبارهٔ free space لازم است. این یافته الزام paid upgrade
ایران یا آلمان را ثابت نمی‌کند.

## وضعیت تحویل و اقدام بعدی

| مورد | code | آزمون | production |
| --- | --- | --- | --- |
| reassessment ظرفیت و جدول نقش‌ها | این گزارش | live read-only + sysstat | هیچ تغییری اعمال نشد |
| control plane مشترک scheduler | هنوز ادغام نشده | نمونهٔ bounded/mock | نصب/فعال نشده |
| remote API-model orchestration | قرارداد/adapter نیازمند تکمیل | جابه‌جایی کامل آزموده نشده | منتقل نشده |
| batch writer | فقط prototype ignored | local load + سه invariant | نصب نشده |
| private HTTPS موجود | از قبل موجود | هر پنج consumer و مسیر برگشت بررسی شد | سرویس‌های قبلی دست‌نخورده |
| runtime/broker نهایی پنل | قابلیت‌های قبلی در branch | این audit اثبات E2E نیست | enrollment/schema/release gates باقی است |

گزینهٔ معماری توصیه‌شده برای مرحلهٔ بعد **shared scheduler control plane** است؛ گزینهٔ
دیگر یک coordinator کوچک مستقل ایران است که process isolation بهتر ولی footprint
بیشتری دارد. این گزارش مجوز اجرای تغییر در production نیست. ابتدا integration، retry/
lease/heartbeat و capture backlog اصلاح و سپس آزمون هم‌زمان workloadهای واقعی روی
محیط ایزوله تکرار شود. فقط یک bottleneck اندازه‌گیری‌شدهٔ باقی‌مانده می‌تواند ضرورت
upgrade را ثابت کند؛ چنین شاهدی برای RAM/CPU میزبان ایران در این بررسی نداریم.

فرمان‌های اجراشده (همهٔ helperها و fixtureها محلی و ignored):

```text
python3 .codex-tmp/capacity-20261121/observe-hosts.py
python3 .codex-tmp/capacity-20261121/history.py
python3 .codex-tmp/capacity-20261121/swap-observe.py
python3 .codex-tmp/capacity-20261121/verify-private-path.py
python3 .codex-tmp/capacity-20261121/check-private-database-boundary.py
python3 .codex-tmp/capacity-20261121/run-internal-client.py baseline
python3 .codex-tmp/capacity-20261121/run-internal-client.py sustained-corrected
python3 .codex-tmp/capacity-20261121/run-internal-client.py sustained-diagnostics-60s
python3 .codex-tmp/capacity-20261121/run-internal-client.py sustained-batched-60s
python3 .codex-tmp/capacity-20261121/summarize-load.py
python3 .codex-tmp/capacity-20261121/summarize-batched.py
python3 .codex-tmp/capacity-20261121/final-host-check.py
docker compose -f .codex-tmp/capacity-20261121/compose.json down --volumes
```

cleanup فقط همان project/network/دادهٔ tmpfs ایزوله را حذف کرد؛ image و شواهد خصوصی
برای بازبینی باقی ماندند. 10 سرویس ایران و چهار سرویس آلمان در بررسی نهایی همان
container ID، started-at و restart-count اولیه را داشتند.
CI source پایه [44914007967](https://github.com/mohammad4242/fitician/actions/runs/44914007967)
موفق بود؛ آن CI پوشش prototype خصوصی یا پذیرش production این معماری نیست.
