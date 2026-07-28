import { pgTable, serial, text, varchar, integer, timestamp, index } from "drizzle-orm/pg-core"
import { sql } from "drizzle-orm"

// ============ 系统表 ============

export const healthCheck = pgTable("health_check", {
  id: serial().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow(),
});

// ============ 可回收火箭 ============

export const rocketCompanies = pgTable("rocket_companies", {
  id: serial().notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  country: varchar("country", { length: 50 }).notNull(),
  foundedYear: varchar("founded_year", { length: 10 }),
  logo: varchar("logo", { length: 500 }),
  website: varchar("website", { length: 500 }),
  description: text("description"),
  valuation: varchar("valuation", { length: 100 }),
  employees: varchar("employees", { length: 50 }),
  achievements: text("achievements"),
  rockets: text("rockets"),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => ({
  countryIdx: index("rocket_companies_country_idx").on(table.country),
}));

export const rocketTimeline = pgTable("rocket_timeline", {
  id: serial().notNull(),
  eventDate: varchar("event_date", { length: 50 }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  description: text("description"),
  company: varchar("company", { length: 255 }),
  country: varchar("country", { length: 50 }),
  status: varchar("status", { length: 50 }),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

// ============ 中美登月 ============

export const moonHighlights = pgTable("moon_highlights", {
  id: serial().notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  content: text("content"),
  country: varchar("country", { length: 50 }),
  sortOrder: integer("sort_order").default(0),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

export const moonComparison = pgTable("moon_comparison", {
  id: serial().notNull(),
  category: varchar("category", { length: 100 }).notNull(),
  china: text("china"),
  usa: text("usa"),
  sortOrder: integer("sort_order").default(0),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

// ============ 中国半导体 ============

export const semiconductorCompanies = pgTable("semiconductor_companies", {
  id: serial().notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  field: varchar("field", { length: 100 }),
  description: text("description"),
  progress: text("progress"),
  sortOrder: integer("sort_order").default(0),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

export const semiconductorTimeline = pgTable("semiconductor_timeline", {
  id: serial().notNull(),
  eventDate: varchar("event_date", { length: 50 }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  description: text("description"),
  company: varchar("company", { length: 255 }),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

// ============ 中国科技 AI ============

export const chinaTechCompanies = pgTable("china_tech_companies", {
  id: serial().notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  field: varchar("field", { length: 100 }),
  description: text("description"),
  products: text("products"),
  sortOrder: integer("sort_order").default(0),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

export const chinaTechTimeline = pgTable("china_tech_timeline", {
  id: serial().notNull(),
  eventDate: varchar("event_date", { length: 50 }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  description: text("description"),
  company: varchar("company", { length: 255 }),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

// ============ 中国大工程 ============

export const megaProjects = pgTable("mega_projects", {
  id: serial().notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  country: varchar("country", { length: 50 }),
  category: varchar("category", { length: 100 }),
  status: varchar("status", { length: 50 }),
  description: text("description"),
  startDate: varchar("start_date", { length: 50 }),
  completionDate: varchar("completion_date", { length: 50 }),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

export const megaProjectTimeline = pgTable("mega_project_timeline", {
  id: serial().notNull(),
  eventDate: varchar("event_date", { length: 50 }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  description: text("description"),
  project: varchar("project", { length: 255 }),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

// ============ 可控核聚变 ============

export const fusionProjects = pgTable("fusion_projects", {
  id: serial().notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  country: varchar("country", { length: 50 }),
  type: varchar("type", { length: 100 }),
  status: varchar("status", { length: 50 }),
  description: text("description"),
  capacity: varchar("capacity", { length: 100 }),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

export const fusionTimeline = pgTable("fusion_timeline", {
  id: serial().notNull(),
  eventDate: varchar("event_date", { length: 50 }).notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  description: text("description"),
  project: varchar("project", { length: 255 }),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

// ============ 科技资本 ============

export const financeCompanies = pgTable("finance_companies", {
  id: serial().notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  ticker: varchar("ticker", { length: 20 }),
  market: varchar("market", { length: 50 }),
  sector: varchar("sector", { length: 100 }),
  marketCap: varchar("market_cap", { length: 100 }),
  description: text("description"),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

export const financeFundingEvents = pgTable("finance_funding_events", {
  id: serial().notNull(),
  companyName: varchar("company_name", { length: 255 }).notNull(),
  amount: varchar("amount", { length: 100 }),
  round: varchar("round", { length: 50 }),
  investors: text("investors"),
  eventDate: varchar("event_date", { length: 50 }),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

export const financeExchangeRates = pgTable("finance_exchange_rates", {
  id: serial().notNull(),
  fromCurrency: varchar("from_currency", { length: 10 }).notNull(),
  toCurrency: varchar("to_currency", { length: 10 }).notNull(),
  rate: varchar("rate", { length: 50 }).notNull(),
  rateDate: varchar("rate_date", { length: 50 }),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
});

// ============ 爬虫数据 ============

export const rawArticles = pgTable("raw_articles", {
  id: serial().notNull(),
  board: varchar("board", { length: 50 }).notNull(),
  source: varchar("source", { length: 100 }).notNull(),
  title: varchar("title", { length: 500 }).notNull(),
  url: varchar("url", { length: 1000 }).notNull(),
  content: text("content"),
  publishedAt: varchar("published_at", { length: 50 }),
  crawledAt: timestamp("crawled_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => ({
  boardIdx: index("raw_articles_board_idx").on(table.board),
  crawledAtIdx: index("raw_articles_crawled_at_idx").on(table.crawledAt),
}));

export const crawlLogs = pgTable("crawl_logs", {
  id: serial().notNull(),
  board: varchar("board", { length: 50 }).notNull(),
  source: varchar("source", { length: 100 }).notNull(),
  status: varchar("status", { length: 20 }).notNull(),
  message: text("message"),
  articlesCount: integer("articles_count"),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
}, (table) => ({
  boardIdx: index("crawl_logs_board_idx").on(table.board),
  createdAtIdx: index("crawl_logs_created_at_idx").on(table.createdAt),
}));

export const boardStatus = pgTable("board_status", {
  id: serial().notNull(),
  board: varchar("board", { length: 50 }).notNull().unique(),
  lastCrawlAt: varchar("last_crawl_at", { length: 50 }),
  articlesCount: integer("articles_count").default(0).notNull(),
  sourcesCount: integer("sources_count").default(0).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true, mode: 'string' }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }),
});
