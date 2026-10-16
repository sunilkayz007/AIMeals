/**
 * RevenueCat wrapper — the ONLY file that talks to react-native-purchases.
 *
 * Trust model: the app never grants a tier itself. A purchase goes
 * Play Billing -> RevenueCat -> POST /api/v1/billing/revenuecat-webhook
 * -> SubscriptionService.apply_revenuecat_event(), and the Upgrade
 * screen then re-reads GET /api/v1/subscription. For that webhook to
 * find the right user, RevenueCat's app_user_id MUST be the AIMeals
 * user's UUID — hence identify() is called with user.id on every
 * session start (see AuthGate in app/_layout.tsx), and anonymous
 * RevenueCat ids are never used for a purchase.
 *
 * Product layout expected in Play Console / RevenueCat:
 *   Play subscriptions `aimeals_plus` and `aimeals_pro`, each with
 *   `monthly` and `annual` base plans, attached as packages to the
 *   RevenueCat "current" offering. RevenueCat reports those as
 *   "<subscriptionId>:<basePlanId>" (e.g. "aimeals_plus:monthly");
 *   tierForProductId() and the backend's tier_for_product_id() both
 *   resolve on the part before the ":".
 *
 * If EXPO_PUBLIC_REVENUECAT_ANDROID_KEY is unset (dev builds, or a
 * build made before the key existed) every function here degrades to
 * "billing unavailable" instead of throwing, so the rest of the app
 * keeps working.
 */
import { Platform } from 'react-native';
import Purchases, {
  LOG_LEVEL,
  PACKAGE_TYPE,
  type CustomerInfo,
  type PurchasesPackage,
} from 'react-native-purchases';
import type { SubscriptionTier } from '../types/subscription';

const ANDROID_API_KEY = process.env.EXPO_PUBLIC_REVENUECAT_ANDROID_KEY ?? '';

let configured = false;
let identifiedUserId: string | null = null;

export type PaidTier = Exclude<SubscriptionTier, 'free'>;
export type BillingPeriod = 'monthly' | 'annual';

export interface TierPackage {
  tier: PaidTier;
  period: BillingPeriod;
  /** Localized price string from Play, e.g. "₹299.00". */
  priceString: string;
  /** Store product id, e.g. "aimeals_plus:monthly". */
  productId: string;
  pkg: PurchasesPackage;
}

export function isBillingAvailable(): boolean {
  return Platform.OS === 'android' && ANDROID_API_KEY.length > 0;
}

/** "aimeals_plus:monthly" / "aimeals_plus_monthly" -> 'plus'. */
export function tierForProductId(productId: string): PaidTier | null {
  const base = productId.split(':')[0].toLowerCase();
  if (base.includes('pro')) return 'pro';
  if (base.includes('plus')) return 'plus';
  return null;
}

function periodForPackage(pkg: PurchasesPackage): BillingPeriod | null {
  // The store's own ISO 8601 billing period ("P1M", "P1Y") is the
  // source of truth — base plan ids are just labels and can be
  // misleading (a base plan named "annual" can bill monthly).
  const isoPeriod = pkg.product.subscriptionPeriod;
  if (isoPeriod === 'P1M' || isoPeriod === 'P4W') return 'monthly';
  if (isoPeriod === 'P1Y' || isoPeriod === 'P12M') return 'annual';
  if (pkg.packageType === PACKAGE_TYPE.MONTHLY) return 'monthly';
  if (pkg.packageType === PACKAGE_TYPE.ANNUAL) return 'annual';
  // Last resort for custom packages: the Play base plan id.
  const basePlan = pkg.product.identifier.split(':')[1] ?? '';
  if (basePlan.includes('month')) return 'monthly';
  if (basePlan.includes('year') || basePlan.includes('annual')) return 'annual';
  return null;
}

/**
 * Configures the SDK (first call) or switches the RevenueCat user
 * (later calls) to the given AIMeals user id. Safe to call repeatedly.
 */
export async function identify(userId: string): Promise<void> {
  if (!isBillingAvailable() || identifiedUserId === userId) return;
  try {
    if (!configured) {
      if (__DEV__) Purchases.setLogLevel(LOG_LEVEL.DEBUG);
      Purchases.configure({ apiKey: ANDROID_API_KEY, appUserID: userId });
      configured = true;
    } else {
      await Purchases.logIn(userId);
    }
    identifiedUserId = userId;
  } catch (err) {
    console.warn('RevenueCat identify failed', err);
  }
}

/** Called on sign-out so the next user never inherits these purchases. */
export async function reset(): Promise<void> {
  if (!configured || identifiedUserId === null) return;
  identifiedUserId = null;
  try {
    await Purchases.logOut();
  } catch {
    // logOut throws if the current user is already anonymous — fine.
  }
}

/** Packages from the RevenueCat "current" offering, sorted Plus -> Pro, monthly -> annual. */
export async function getTierPackages(): Promise<TierPackage[]> {
  if (!configured) return [];
  const offerings = await Purchases.getOfferings();
  const packages = offerings.current?.availablePackages ?? [];
  const result: TierPackage[] = [];
  for (const pkg of packages) {
    const tier = tierForProductId(pkg.product.identifier);
    const period = periodForPackage(pkg);
    if (!tier || !period) continue;
    result.push({
      tier,
      period,
      priceString: pkg.product.priceString,
      productId: pkg.product.identifier,
      pkg,
    });
  }
  const order = (p: TierPackage) => (p.tier === 'plus' ? 0 : 2) + (p.period === 'monthly' ? 0 : 1);
  return result.sort((a, b) => order(a) - order(b));
}

export type PurchaseOutcome = 'purchased' | 'cancelled';

/**
 * Starts the Play purchase sheet. If the user already has an active
 * AIMeals subscription (e.g. Plus -> Pro), Play requires it to be
 * REPLACED rather than bought alongside, so the old subscription id
 * is passed as product-change info.
 */
export async function purchase(pkg: PurchasesPackage): Promise<PurchaseOutcome> {
  let productChangeInfo = null;
  try {
    const info = await Purchases.getCustomerInfo();
    const current = info.activeSubscriptions.find((id) => tierForProductId(id) !== null);
    if (current && current !== pkg.product.identifier) {
      productChangeInfo = { oldProductIdentifier: current.split(':')[0] };
    }
  } catch {
    // Can't read current subscriptions — attempt a plain purchase;
    // Play itself will reject a duplicate subscription.
  }
  try {
    await Purchases.purchasePackage(pkg, null, productChangeInfo);
    return 'purchased';
  } catch (err: any) {
    if (err?.userCancelled) return 'cancelled';
    throw err;
  }
}

export async function restore(): Promise<CustomerInfo | null> {
  if (!configured) return null;
  return Purchases.restorePurchases();
}
