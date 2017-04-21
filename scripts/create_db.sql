create table if not exists patents(
    PNum integer primary key unique
);

create table if not exists patentdata(
    PNum integer not null,
    FieldType varchar(10),
    AppNum int,
    SeriesCode character,
    AppDate integer, -- Proleptic Gregorian ordinal date.
    Title text,
    foreign key (PNum) references patents(PNum)
);

create table if not exists texttypes (
    Id integer primary key autoincrement,
    Name varchar(20) not NULL
);

create table if not exists fulltexts (
    Id integer primary key autoincrement,
    PatentId integer not NULL,
    TextType integer not NULL,
    Body text not NULL,
    foreign key(PatentId) references patents(PNum),
    foreign key (TextType) references texttypes(Id)
);

create table if not exists citations (
    CitingPNum integer not NULL,
    CitedPNum integer not NULL,
    foreign key (CitingPNum) references patents(PNum),
    foreign key (CitedPNum) references patents(PNum)
);

create index if not exists date_index on patentdata (AppDate);

insert into texttypes values (NULL, 'ABSTRACT');
insert into texttypes values (NULL, 'BRIEF SUMMARY');
insert into texttypes values (NULL, 'DESCRIPTION');
insert into texttypes values (NULL, 'CLAIMS');