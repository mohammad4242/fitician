import { Link } from "react-router-dom";

import androidGymImage from "../../../../mobile/assets/landing/pic_land.jpg";
import "./iosPwaWelcome.css";

/** Mirrors mobile/public/PublicLandingScreen without the public Web shell. */
export function IosPwaWelcome() {
  return (
    <main className="ios-pwa-welcome" data-testid="ios-pwa-welcome" dir="rtl" lang="fa">
      <img className="ios-pwa-welcome__background" data-testid="public-entry-background" src={androidGymImage} alt="" aria-hidden="true" />
      <div className="ios-pwa-welcome__actions">
        <Link className="ios-pwa-welcome__start" to="/get-started">شروع کنیم</Link>
        <Link className="ios-pwa-welcome__login" to="/login">حساب داری؟ <span>ورود</span></Link>
      </div>
    </main>
  );
}
