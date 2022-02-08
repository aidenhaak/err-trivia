BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Questions" (
	"Id"	INTEGER NOT NULL,
	"Question"	TEXT NOT NULL,
	"Answer"	TEXT NOT NULL,
	PRIMARY KEY("Id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Users" (
	"Id"	INTEGER NOT NULL,
	"Name"	TEXT NOT NULL,
	PRIMARY KEY("Id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Games" (
	"Id"	INTEGER NOT NULL,
	"Name"	TEXT NOT NULL,
	PRIMARY KEY("Id")
);
CREATE TABLE IF NOT EXISTS "GameStatistics" (
	"GameId"	INTEGER NOT NULL,
	"UserId"	INTEGER NOT NULL,
	"Points"	INTEGER NOT NULL,
	FOREIGN KEY("GameId") REFERENCES "Games"("Id"),
	FOREIGN KEY("UserId") REFERENCES "Users"("Id"),
	PRIMARY KEY("GameId","UserId")
);
CREATE TABLE IF NOT EXISTS "UserAliases" (
	"OriginalId"	INTEGER NOT NULL,
	"AliasId"	INTEGER NOT NULL,
	FOREIGN KEY("OriginalId") REFERENCES "Users"("Id"),
	FOREIGN KEY("AliasId") REFERENCES "Users"("Id"),
	CHECK("OriginalId" <> "AliasId"),
	PRIMARY KEY("OriginalId","AliasId")
);
CREATE INDEX IF NOT EXISTS "User_Name_Index" ON "Users" (
	"Name"	ASC
);
CREATE INDEX IF NOT EXISTS "Game_Name_Index" ON "Games" (
	"Name"	ASC
);
COMMIT;
