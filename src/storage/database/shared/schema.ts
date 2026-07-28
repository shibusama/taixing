import { pgTable, serial, text, varchar, integer, timestamp, date } from "drizzle-orm/pg-core"
import { sql } from "drizzle-orm"

// ============ 系统表 ============

export const healthCheck = pgTable("health_check", {
  id: serial().primaryKey(),
  updatedAt: timestamp("updated_at", { withTimezone: true, mode: 'string' }).defaultNow(),
});

// ============ 板块状态 ============

export const boardStatus = pgTable("board_status", {
  boardId: text("board_id"),
  lastCrawledAt: text("last_crawled_at"),
  newItemsCount: text("new_items_count"),
  totalSources: text("total_sources"),
  errorSources: text("error_sources"),
  lastMessage: text("last_message"),
  rocketIntro: text("rocket_intro"),
});

// ============ 可回收火箭 ============

export const rocketCompanies = pgTable("rocket_companies", {
  id: integer("id").primaryKey(),
  rocket: text("rocket"),
  company: text("company"),
  country: text("country"),
  fuel: text("fuel"),
  diameter: text("diameter"),
  thrust: text("thrust"),
  leo: text("leo"),
  recovery: text("recovery"),
  status: text("status"),
  key: text("key"),
  sortOrder: text("sort_order"),
});

export const rocketTimeline = pgTable("rocket_timeline", {
  id: integer("id").primaryKey(),
  period: text("period"),
  eventDate: text("event_date"),
  title: text("title"),
  description: text("description"),
  color: text("color"),
  badge: text("badge"),
  done: text("done"),
  sortOrder: text("sort_order"),
});

// ============ 中美登月 ============

export const moonHighlights = pgTable("moon_highlights", {
  id: integer("id").primaryKey(),
  num: text("num"),
  label: text("label"),
  color: text("color"),
  sortOrder: text("sort_order"),
});

export const moonComparison = pgTable("moon_comparison", {
  id: serial().primaryKey(),
  aspect: varchar("aspect"),
  chinaValue: text("china_value"),
  usaValue: text("usa_value"),
  notes: text("notes"),
  createdAt: timestamp("created_at", { mode: 'string' }).defaultNow(),
});

// ============ 中国半导体 ============

export const semiconductorHighlights = pgTable("semiconductor_highlights", {
  id: integer("id").primaryKey(),
  num: text("num").notNull(),
  label: text("label").notNull(),
  color: text("color"),
  sortOrder: integer("sort_order").default(0),
});

export const semiconductorTabHighlights = pgTable("semiconductor_tab_highlights", {
  id: integer("id").primaryKey(),
  tabId: text("tab_id").notNull(),
  num: text("num").notNull(),
  label: text("label").notNull(),
  color: text("color"),
  sortOrder: integer("sort_order").default(0),
});

export const semiconductorTabProgress = pgTable("semiconductor_tab_progress", {
  id: integer("id").primaryKey(),
  tabId: text("tab_id").notNull(),
  year: text("year").notNull(),
  value: text("value"),
  label: text("label"),
  cls: text("cls"),
  sortOrder: integer("sort_order").default(0),
});

export const semiconductorTechnologies = pgTable("semiconductor_technologies", {
  id: serial().primaryKey(),
  name: varchar("name").notNull(),
  category: varchar("category"),
  description: text("description"),
  status: varchar("status"),
  createdAt: timestamp("created_at", { mode: 'string' }).defaultNow(),
});

export const semiconductorTimeline = pgTable("semiconductor_timeline", {
  id: serial().primaryKey(),
  eventDate: date("event_date"),
  company: varchar("company"),
  eventType: varchar("event_type"),
  description: text("description"),
  createdAt: timestamp("created_at", { mode: 'string' }).defaultNow(),
});

// ============ 中国科技 AI ============

export const chinaTechHighlights = pgTable("china_tech_highlights", {
  id: integer("id").primaryKey(),
  num: text("num").notNull(),
  label: text("label").notNull(),
  color: text("color"),
  sortOrder: integer("sort_order").default(0),
});

export const chinaTechLlm = pgTable("china_tech_llm", {
  id: integer("id").primaryKey(),
  model: text("model").notNull(),
  company: text("company").notNull(),
  params: text("params"),
  contextWindow: text("context_window"),
  coding: text("coding"),
  math: text("math"),
  arena: text("arena"),
  opensource: text("opensource"),
  price: text("price"),
  hiFields: text("hi_fields"),
  sortOrder: integer("sort_order").default(0),
});

export const chinaTechTimeline = pgTable("china_tech_timeline", {
  id: serial().primaryKey(),
  eventDate: date("event_date"),
  company: varchar("company"),
  eventType: varchar("event_type"),
  description: text("description"),
  createdAt: timestamp("created_at", { mode: 'string' }).defaultNow(),
});

// ============ 中国大工程 ============

export const megaProjects = pgTable("mega_projects", {
  id: integer("id").primaryKey(),
  tabId: text("tab_id"),
  emoji: text("emoji"),
  projectName: text("project_name"),
  targetId: text("target_id"),
  status: text("status"),
  statusClass: text("status_class"),
  sortOrder: text("sort_order"),
});

export const megaProjectHighlights = pgTable("mega_project_highlights", {
  id: integer("id").primaryKey(),
  num: text("num").notNull(),
  label: text("label").notNull(),
  color: text("color"),
  sortOrder: integer("sort_order").default(0),
});

export const megaProjectMilestones = pgTable("mega_project_milestones", {
  id: integer("id").primaryKey(),
  projectId: integer("project_id").notNull(),
  marker: text("marker"),
  eventDate: text("event_date"),
  badge: text("badge"),
  badgeClass: text("badge_class"),
  title: text("title"),
  sortOrder: integer("sort_order").default(0),
});

// ============ 可控核聚变 ============

export const fusionHighlights = pgTable("fusion_highlights", {
  id: integer("id").primaryKey(),
  num: text("num").notNull(),
  label: text("label").notNull(),
  color: text("color"),
  sortOrder: integer("sort_order").default(0),
});

export const fusionTimeline = pgTable("fusion_timeline", {
  id: integer("id").primaryKey(),
  region: text("region"),
  regionLabel: text("region_label"),
  eventDate: text("event_date"),
  title: text("title"),
  description: text("description"),
  color: text("color"),
  sortOrder: text("sort_order"),
});

// ============ 科技资本 ============

export const financeGrids = pgTable("finance_grids", {
  id: integer("id").primaryKey(),
  section: text("section").notNull(),
  key: text("key").notNull(),
  value: text("value").notNull(),
  sortOrder: integer("sort_order").default(0),
});

export const financeHighlights = pgTable("finance_highlights", {
  id: integer("id").primaryKey(),
  section: text("section").notNull(),
  label: text("label").notNull(),
  num: text("num").notNull(),
  sub: text("sub"),
  color: text("color"),
  sortOrder: integer("sort_order").default(0),
});

export const financeSections = pgTable("finance_sections", {
  id: integer("id").primaryKey(),
  section: text("section").notNull(),
  tag: text("tag"),
  name: text("name"),
  en: text("en"),
  description: text("description"),
  sortOrder: integer("sort_order").default(0),
});

// ============ 爬虫数据 ============

export const rawArticles = pgTable("raw_articles", {
  id: integer("id").primaryKey(),
  boardId: text("board_id"),
  source: text("source"),
  title: text("title"),
  url: text("url"),
  summary: text("summary"),
  date: text("date"),
  rawJson: text("raw_json"),
  dedupKey: text("dedup_key"),
  isNew: text("is_new"),
  createdAt: text("created_at"),
});

export const crawlLogs = pgTable("crawl_logs", {
  id: serial().primaryKey(),
  boardId: varchar("board_id"),
  status: varchar("status"),
  sourceName: varchar("source_name"),
  itemsCount: integer("items_count").default(0),
  errorMessage: text("error_message"),
  startedAt: timestamp("started_at", { mode: 'string' }),
  finishedAt: timestamp("finished_at", { mode: 'string' }),
  createdAt: timestamp("created_at", { mode: 'string' }).defaultNow(),
});
