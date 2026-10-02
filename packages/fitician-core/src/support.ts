import type { components } from './generated/api.js';
import type { TransportRequest } from './transport.js';
export type SupportLanguage = 'fa' | 'en';
export type SupportTicket = components['schemas']['TicketResponse'];
export type SupportMessage = components['schemas']['SupportMessageResponse'];
export type SupportDetail = components['schemas']['TicketDetail'];
export type SupportCategory = components['schemas']['SupportCategory'];
export type SupportStatus = components['schemas']['SupportStatus'];
export type SupportRequest = <T>(input: TransportRequest) => Promise<T>;
export const supportCategories: readonly SupportCategory[] = ['technical','account','billing','workout','nutrition','body_analysis','feature_request','other'];
export const supportStatuses: readonly SupportStatus[] = ['open','awaiting_user','resolved','closed'];
export const supportCopy = {
  fa: { title:'پشتیبانی و ارتباط با ما', hero:'چطور می‌تونیم کمکت کنیم؟', help:'مرکز راهنما', tickets:'تیکت‌های من', create:'ارسال درخواست', search:'جست‌وجو در مرکز راهنما', all:'همه موضوع‌ها', empty:'هنوز درخواستی ثبت نکرده‌ای', emptyHint:'اگر به کمک نیاز داری، درخواستت را بفرست. پاسخ تیم فیتیشن اینجا نمایش داده می‌شود.', noResults:'نتیجه‌ای پیدا نشد. عبارت دیگری را جست‌وجو کن.', subject:'موضوع', description:'توضیحات', category:'موضوع درخواست', message:'متن پیام', send:'ارسال پیام', loading:'در حال بارگذاری…', retry:'تلاش دوباره', error:'ارتباط برقرار نشد. دوباره تلاش کن.', older:'نمایش موارد قدیمی‌تر', refresh:'به‌روزرسانی', member:'شما', admin:'پشتیبانی فیتیشن', closed:'این درخواست بسته شده است. برای موضوع جدید یک درخواست تازه بفرست.', resolved:'این درخواست حل شده است. اگر هنوز به کمک نیاز داری، همین‌جا پاسخ بده.', privacy:'فقط توضیح لازم را بنویس. عکس بدن، مدارک پزشکی، رمز عبور و اطلاعات پرداخت را ارسال نکن.', login:'ورود برای ارسال درخواست', back:'بازگشت', activity:'آخرین فعالیت', count:'درخواست باز', status:'وضعیت', queue:'صف پشتیبانی', save:'ثبت وضعیت', instagram:'اینستاگرام' },
  en: { title:'Support & contact', hero:'How can we help?', help:'Help Center', tickets:'My tickets', create:'Submit a request', search:'Search the Help Center', all:'All topics', empty:'No requests yet', emptyHint:'Send a request when you need help. Replies from Fitician will appear here.', noResults:'No results. Try another search.', subject:'Subject', description:'Description', category:'Request category', message:'Message', send:'Send message', loading:'Loading…', retry:'Try again', error:'Could not connect. Please try again.', older:'Load older items', refresh:'Refresh', member:'You', admin:'Fitician Support', closed:'This request is closed. Submit a new request for a new issue.', resolved:'This request is resolved. Reply here if you still need help.', privacy:'Share only what is needed. Do not send body photos, medical documents, passwords or payment details.', login:'Sign in to submit a request', back:'Back', activity:'Last activity', count:'Open requests', status:'Status', queue:'Support queue', save:'Save status', instagram:'Instagram' },
} as const;
export const supportCategoryLabels: Record<SupportLanguage, Record<SupportCategory,string>> = {
 fa:{ technical:'مشکلات فنی',account:'حساب و ورود',billing:'اشتراک و پرداخت',workout:'برنامه تمرینی',nutrition:'تغذیه',body_analysis:'تحلیل بدن',feature_request:'پیشنهاد قابلیت',other:'سایر' },
 en:{ technical:'Technical issues',account:'Account & sign-in',billing:'Subscription & billing',workout:'Training plan',nutrition:'Nutrition',body_analysis:'Body Analysis',feature_request:'Feature request',other:'Other' },
};
export const supportStatusLabels: Record<SupportLanguage, Record<SupportStatus,string>> = {
 fa:{open:'باز',awaiting_user:'منتظر پاسخ شما',resolved:'حل‌شده',closed:'بسته‌شده'},
 en:{open:'Open',awaiting_user:'Awaiting your reply',resolved:'Resolved',closed:'Closed'},
};
export const helpCategories = ['getting-started','account','billing','workout','nutrition','body-analysis','technical','privacy'] as const;
export type HelpCategory = typeof helpCategories[number];
export const helpCategoryLabels: Record<SupportLanguage,Record<HelpCategory,string>> = {
 fa:{'getting-started':'شروع کار با فیتیشن',account:'حساب و ورود',billing:'اشتراک و پرداخت',workout:'برنامه تمرینی',nutrition:'تغذیه','body-analysis':'تحلیل بدن',technical:'مشکلات فنی',privacy:'حریم خصوصی و حذف حساب'},
 en:{'getting-started':'Getting started',account:'Account & sign-in',billing:'Subscription & billing',workout:'Training',nutrition:'Nutrition','body-analysis':'Body Analysis',technical:'Technical issues',privacy:'Privacy & account deletion'},
};
export interface HelpArticle { id:string; category:HelpCategory; content:Record<SupportLanguage,{title:string; keywords:string[]; paragraphs:string[]}> }
function article(id:string, category:HelpCategory, faTitle:string, enTitle:string, faBody:string, enBody:string, faKeywords:string[] = [], enKeywords:string[] = []):HelpArticle {
 return {id,category,content:{fa:{title:faTitle,keywords:faKeywords,paragraphs:faBody.split('\n')},en:{title:enTitle,keywords:enKeywords,paragraphs:enBody.split('\n')}}};
}
/** Stable IDs and structured locale content can later be served by an article API. */
export const helpArticles:readonly HelpArticle[] = [
 article('getting-started','getting-started','از کجا شروع کنم؟','How do I get started?','ابتدا پروفایل و هدف خود را کامل کن. در صفحه امروز، کارهای پیشنهادی و وضعیت برنامه‌ات را می‌بینی. بخش‌های تمرین و تغذیه بر اساس محصول انتخابی تو نمایش داده می‌شوند.','Complete your profile and goal first. Today shows suggested actions and your plan status. Training and nutrition sections depend on your selected product.'),
 article('account-access','account','نمی‌توانم وارد حسابم شوم','I cannot sign in','از همان روش ورود و همان شماره یا ایمیلی استفاده کن که هنگام ثبت‌نام استفاده کرده‌ای. برای حساب رمزدار، گزینه بازیابی رمز را در صفحه ورود انتخاب کن.\nاگر به حساب دسترسی نداری، از راه‌های تماس عمومی این صفحه کمک بگیر. رمز عبور یا کد ورودت را برای کسی ارسال نکن.','Use the same sign-in method and phone number or email used when registering. For password accounts, select password recovery on the sign-in page.\nIf you cannot access your account, use the public contact details on this page. Never share your password or sign-in code.', ['رمز','ایمیل','شماره','کد'], ['login','password','email','OTP']),
 article('billing-access','billing','پرداخت کرده‌ام اما دسترسی فعال نشده','I paid but access is not active','وضعیت سفارش و اشتراک را در بخش بیشتر بررسی کن. اگر پرداخت موفق بوده و دسترسی فعال نیست، یک تیکت در دسته اشتراک و پرداخت بفرست و شماره سفارش را بنویس. اطلاعات کارت یا رمز پرداخت را ارسال نکن.','Check your order and subscription status in More. If payment succeeded but access is inactive, submit a billing ticket with the order reference. Do not send card details or payment passwords.'),
 article('workout-schedule','workout','چطور جلسه تمرین را مدیریت کنم؟','How do I manage training sessions?','برنامه و جلسه‌های زمان‌بندی‌شده را در بخش تمرین باز کن. پس از تمرین، وضعیت همان جلسه را ثبت کن. اگر لازم است روز تمرین تغییر کند، از جابه‌جایی جلسه استفاده کن. لازم نیست تک‌تک ست‌ها را ثبت کنی.\nبرای سؤال تخصصی درباره برنامه، از گفت‌وگوی همان برنامه استفاده کن. تیکت پشتیبانی برای مشکلات حساب و محصول است.','Open Training to view your plan and scheduled sessions. After training, record the session status. Use rescheduling when a training day needs to change. You do not need to log every set.\nUse the program conversation for specialist questions about your plan. Support tickets are for account and product issues.'),
 article('nutrition-tracking','nutrition','ثبت تغذیه چگونه کار می‌کند؟','How does nutrition tracking work?','در بخش ثبت تغذیه، وعده‌ها و مصرف واقعی خود را برای همان روز ثبت و بررسی کن. روزی که چیزی ثبت نشده، به معنای صفر کالری نیست.\nپرسش تخصصی درباره برنامه غذایی را در گفت‌وگوی برنامه مطرح کن.','In nutrition tracking, record and review meals and actual intake for the selected day. A day without records does not mean zero calories.\nAsk specialist nutrition-plan questions in the program conversation.'),
 article('body-analysis','body-analysis','چگونه تحلیل بدن جدید ثبت کنم؟','How do I start a Body Analysis?','بخش تحلیل بدن را باز کن و راهنمای ثبت عکس را دنبال کن. جلسه‌های قبلی، نتایج و مقایسه‌ها در تاریخچه در دسترس‌اند.\nتحلیل عکس یک برآورد بصری است و جایگزین اندازه‌گیری یا ارزیابی پزشکی نیست. عکس بدن را در تیکت پشتیبانی ارسال نکن.','Open Body Analysis and follow the photo capture guide. Previous sessions, results and comparisons remain available in history.\nPhoto analysis is a visual estimate, not a substitute for measurement or medical assessment. Do not send body photos in support tickets.', ['عکس','تصویر','مقایسه'], ['photo','capture','comparison']),
 article('technical-loading','technical','صفحه بارگذاری نمی‌شود','A page will not load','اتصال اینترنت را بررسی کن و دوباره تلاش کن. در وب، صفحه را تازه‌سازی کن؛ در موبایل، برنامه را ببند و باز کن. اگر مشکل ادامه دارد، نام صفحه و مراحل رخ دادن مشکل را در تیکت بنویس. نسخه برنامه و نوع پلتفرم در صورت دسترس بودن خودکار همراه درخواست ارسال می‌شود.','Check your internet connection and try again. On Web, refresh the page; on Mobile, close and reopen the app. If the problem continues, describe the page and steps in a ticket. Available app version and platform information is included automatically.'),
 article('privacy-deletion','privacy','چطور حسابم را حذف کنم؟','How do I delete my account?','در بخش بیشتر، گزینه حذف حساب را باز کن و توضیحات مهلت بازگشت و وضعیت درخواست را بخوان. جزئیات استفاده از داده‌ها در سیاست حریم خصوصی آمده است. اگر امکان ورود نداری، از راه تماس عمومی کمک بگیر.','Open Delete account in More and review the grace period and request status. The privacy policy explains data handling. If you cannot sign in, use the public contact channel.', ['حذف','داده','حریم'], ['delete account','privacy','data']),
];
function normalize(value:string):string { return value.normalize('NFKC').replace(/[يى]/g,'ی').replace(/ك/g,'ک').replace(/[\u064B-\u065F\u0670]/g,'').replace(/\u200c/g,' ').toLowerCase().trim(); }
export function searchHelp(language:SupportLanguage, query:string, category?:HelpCategory):HelpArticle[] {
 const terms=normalize(query).split(/\s+/).filter(Boolean);
 return helpArticles.filter(a=> (!category||a.category===category)&&terms.every(term=>normalize([a.content[language].title,...a.content[language].keywords,...a.content[language].paragraphs].join(' ')).includes(term)));
}
export function createSupportApi(request:SupportRequest, admin=false) {
 const root=`/api/v1/support/${admin?'admin/':''}tickets`;
 const path=(id:string)=>`${root}/${encodeURIComponent(id)}`;
 return {
 list:(filters:{status?:SupportStatus;category?:SupportCategory;search?:string;before?:string}={})=>{
  const query=Object.entries(filters).filter(([,v])=>v!==undefined&&v!=='').map(([k,v])=>`${k}=${encodeURIComponent(v!)}`).join('&');
  return request<components['schemas']['TicketPage']>({path:root+(query?'?'+query:'')});
 },
 create:(input:components['schemas']['TicketInput'])=>request<SupportTicket>({path:root,method:'POST',body:{...input,metadata:input.metadata?{...input.metadata}:null}}),
 detail:(id:string,before?:string)=>request<SupportDetail>({path:path(id)+(before?'?before='+encodeURIComponent(before):'')}),
 reply:(id:string,body:string,requestId:string)=>request<SupportMessage>({path:path(id)+'/messages',method:'POST',body:{body,request_id:requestId}}),
 read:(id:string,messageId:string)=>request<void>({path:path(id)+'/read',method:'PUT',body:{message_id:messageId}}),
 status:(id:string,status:SupportStatus,requestId:string)=>request<SupportTicket>({path:path(id)+'/status',method:'PATCH',body:{status,request_id:requestId}}),
 };
}
export function mergeSupportMessages(first:readonly SupportMessage[],second:readonly SupportMessage[]):SupportMessage[] {
 return [...new Map([...first,...second].map(m=>[m.id,m])).values()].sort((a,b)=>Date.parse(a.created_at)-Date.parse(b.created_at)||a.id.localeCompare(b.id));
}
export { supportContacts } from './public-contacts.js';
export function isSupportTicketId(value:unknown):value is string {
 return typeof value==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}
export function supportTicketDestination(event:string,data:unknown,platform:'web'|'mobile'):string|null {
 if(event!=='support_ticket_reply'||typeof data!=='object'||data===null)return null;
 const id=(data as Record<string,unknown>).ticket_id;
 return isSupportTicketId(id)?`${platform==='web'?'/support/tickets':'/member/support-ticket'}/${id}`:null;
}
