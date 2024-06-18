#define NJ natural join
#define Joined zoos NJ animals NJ profiles
#define top \
    select *, nc+5*nr as score                                                                          \
    from (                                                                                              \
        select commons.animal_name as common, commons.n as nc, rares.animal_name as rare, rares.n as nr \
        from (                                                                                          \
            select animal_id, animal_name, sum(amount) as n                                             \
            from zoos NJ animals NJ profiles NJ users                                                   \
            where not is_rare and user_name == '{discord_user_name}'                                    \
            group by animal_id                                                                          \
        ) as commons                                                                                    \
        join (                                                                                          \
            select animal_common, animal_name, sum(amount) as n                                         \
            from zoos NJ animals NJ profiles NJ users                                                   \
            where is_rare and user_name == '{discord_user_name}'                                        \
            group by animal_id                                                                          \
        ) as rares                                                                                      \
        on animal_id == animal_common                                                                   \
    ) order by score desc
#define todo \
    select (                        \
        substr(profile_name,1,2)    \
        || " "                      \
        || thing                    \
        || " <t:"                   \
        || utctimestamp             \
        || ":R>"                    \
        || " (<t:"                  \
        || utctimestamp             \
        || ":f>)"                   \
    ) as magic_lines                \
    from todos NJ profiles NJ users \
    where user_name == '{discord_user_name}'
#define td todo
