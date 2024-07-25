#define NJ natural join
#define Joined zoos NJ animals NJ profiles NJ users
#define top(cond) \
    select *, nc+5*nr as score                                                                          \
    from (                                                                                              \
        select commons.animal_name as common, commons.n as nc, rares.animal_name as rare, rares.n as nr \
        from (                                                                                          \
            select animal_id, animal_name, sum(amount) as n                                             \
            from zoos NJ animals NJ profiles NJ users                                                   \
            where not is_rare and (cond)                                                                \
            group by animal_id                                                                          \
        ) as commons                                                                                    \
        join (                                                                                          \
            select animal_common, animal_name, sum(amount) as n                                         \
            from zoos NJ animals NJ profiles NJ users                                                   \
            where is_rare and (cond)                                                                    \
            group by animal_id                                                                          \
        ) as rares                                                                                      \
        on animal_id == animal_common                                                                   \
    ) order by score desc

#define mytop top(user_name == '{discord_user_name}')

#define todo \
    select (                        \
        profile_icon                \
        || " " ||                   \
        substr(profile_name,1,2)    \
        || " "                      \
        || emoji                    \
        || " "                      \
        || thing                    \
        || " <t:"                   \
        || utctimestamp             \
        || ":R>"                    \
        || " (<t:"                  \
        || utctimestamp             \
        || ":f>)"                   \
        || (CASE                    \
                WHEN datetime(utcdatetime)<datetime('now') THEN " ⏰" \
                ELSE ""             \
            END)                    \
    ) as magic_lines                \
    from todos NJ profiles NJ users \
    where user_name == '{discord_user_name}'

#define todo_within(delay) todo and datetime(utcdatetime)<datetime('now',#delay) order by utctimestamp
#define todo_soon todo_within(10 hours)

#define td todo
#define tdw todo_within
#define tds todo_soon
